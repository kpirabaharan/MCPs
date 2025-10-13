import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client
from openai import OpenAI
from logger import get_logger

load_dotenv()


logger = get_logger("weather_mcp_client")


def _schema_to_dict(schema: Any) -> Dict[str, Any]:
    """Convert MCP tool input schema objects to plain dictionaries."""
    if schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(schema, dict):
        return schema
    dump = getattr(schema, "model_dump", None)
    if callable(dump):
        return dump()
    as_dict = getattr(schema, "dict", None)
    if callable(as_dict):
        return as_dict()
    if hasattr(schema, "__dict__"):
        return {k: v for k, v in vars(schema).items() if not k.startswith("_")}
    return {"type": "object", "properties": {}}


def _flatten_tool_content(content: Any) -> str:
    """Turn MCP tool result content into a printable string."""
    if not content:
        return ""

    parts: List[str] = []
    for item in content:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")

        if item_type == "text":
            text = getattr(item, "text", None)
            if text is None and isinstance(item, dict):
                text = item.get("text")
            if text:
                parts.append(text)
        else:
            parts.append(str(item))

    return "\n".join(part for part in parts if part).strip()


class MCPClient:
    def __init__(self) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        base_url = os.getenv("API_BASE")
        if not base_url:
            logger.error("API_BASE is not set; cannot initialize MCPClient")
            raise RuntimeError("API_BASE is not set; point it at your Ollama endpoint.")

        api_key = os.getenv("API_KEY")
        if not api_key:
            # Many local DeepSeek deployments ignore the key but the OpenAI SDK expects something.
            api_key = "not-required"

        self.model = os.getenv("MODEL", "llama3.1:8b")
        logger.info("Initializing MCPClient targeting %s", self.model)
        self.llm = OpenAI(base_url=base_url, api_key=api_key)

    async def connect_to_server(self, server_target: str) -> None:
        """Connect to an MCP server over stdio or HTTP transport."""
        if server_target.startswith(("http://", "https://")):
            await self._connect_http_server(server_target)
            return

        await self._connect_stdio_server(server_target)

    async def _connect_stdio_server(self, server_script_path: str) -> None:
        """Connect to a local MCP server launched via stdio."""
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read, write = transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = [tool.name for tool in response.tools]
        logger.info("Connected to stdio server %s with tools: %s", server_script_path, tools)

    async def _connect_http_server(self, server_url: str) -> None:
        """Connect to an MCP server exposed via Streamable HTTP transport."""
        headers = None
        headers_env = os.getenv("MCP_HTTP_HEADERS")
        if headers_env:
            try:
                headers = json.loads(headers_env)
                if not isinstance(headers, dict):
                    raise ValueError
                headers = {str(k): str(v) for k, v in headers.items()}
            except ValueError as exc:
                raise ValueError("MCP_HTTP_HEADERS must be JSON object of header names and values") from exc

        transport = await self.exit_stack.enter_async_context(streamablehttp_client(server_url, headers=headers))
        read, write, get_session_id = transport

        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = [tool.name for tool in response.tools]

        session_id = get_session_id()
        if session_id:
            logger.info("Connected to HTTP server %s (session %s) with tools: %s", server_url, session_id, tools)
        else:
            logger.info("Connected to HTTP server %s with tools: %s", server_url, tools)

    async def process_query(self, query: str) -> str:
        if self.session is None:
            raise RuntimeError("Not connected to any MCP server.")

        logger.info("Processing query: %s", query)
        # Refresh the tool catalog so the orchestrator sees up-to-date capabilities.
        list_response = await self.session.list_tools()
        for tool in list_response.tools:
            logger.info("Processing tool: %s", tool.name)
            logger.info("Description: %s", tool.description)
            logger.info("Input Parameters: %s", _schema_to_dict(tool.inputSchema))

        # Present each MCP tool to the model using the OpenAI tool/function schema.
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": _schema_to_dict(tool.inputSchema),
                },
            }
            for tool in list_response.tools
        ]

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": query},
        ]

        final_chunks: List[str] = []

        turn_index = 1
        # Drive the function-calling loop until the model no longer requests tools.
        while True:
            logger.info(
                "Starting completion turn %d with %d message(s) and %d tool(s)",
                turn_index,
                len(messages),
                len(available_tools),
            )
            # Assemble the request payload that the OpenAI-compatible API expects.
            request_kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if available_tools:
                request_kwargs["tools"] = available_tools
                request_kwargs["tool_choice"] = "auto"

            # Ask the model for the next turn and capture both text and tool calls.
            completion = self.llm.chat.completions.create(**request_kwargs)
            message = completion.choices[0].message
            content_text = message.content or ""
            logger.info(
                "Model reply on turn %d: role=%s chars=%d tool_calls=%d",
                turn_index,
                message.role,
                len(content_text),
                len(message.tool_calls or []),
            )
            if content_text.strip():
                final_chunks.append(content_text.strip())

            tool_calls = message.tool_calls or []
            if not tool_calls:
                logger.info("Turn %d produced no tool calls; ending conversation with model", turn_index)
                break

            # Record the assistant message, including tool call metadata, in the transcript.
            assistant_message: Dict[str, Any] = {"role": "assistant", "content": content_text, "tool_calls": []}

            for tool_call in tool_calls:
                assistant_message["tool_calls"].append(
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                )
            messages.append(assistant_message)

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                try:
                    # Parse the arguments the model supplied for this tool call.
                    logger.info(
                        "Turn %d tool call %s: name=%s raw_args=%s",
                        turn_index,
                        tool_call.id,
                        tool_name,
                        tool_call.function.arguments,
                    )
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Failed to parse arguments for tool {tool_name}: {exc}") from exc

                # Execute the MCP tool and fold the response back into the model dialogue.
                logger.info("Invoking MCP tool %s with parsed args %s", tool_name, arguments)
                result = await self.session.call_tool(tool_name, arguments)
                tool_output = _flatten_tool_content(getattr(result, "content", None))
                summary = f"[Tool {tool_name} called with args {arguments}]"
                final_chunks.append(summary)
                if tool_output:
                    logger.info(
                        "Tool %s returned %d character(s) of content", tool_name, len(tool_output)
                    )
                    final_chunks.append(tool_output)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_output or "(no output)",
                    }
                )

                logger.info("Tool %s returned %s", tool_name, "output" if tool_output else "no output")

            turn_index += 1

        # Merge everything we want to show the user into a final string payload.
        result_text = "\n".join(chunk for chunk in final_chunks if chunk)
        logger.info("Query completed with %d characters of output", len(result_text))
        return result_text

    async def chat_loop(self) -> None:
        logger.info("MCP Client Started! Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
            except EOFError:
                logger.info("Received EOF; exiting chat loop.")
                break

            if query.lower() in {"quit", "exit"}:
                break

            if not query:
                continue

            try:
                response = await self.process_query(query)
                if response:
                    logger.info("Model response:\n%s", response)
                else:
                    logger.info("(No response returned)")
            except Exception as exc:
                logger.exception("Error while processing query")

    async def cleanup(self) -> None:
        logger.info("Cleaning up MCP client resources")
        await self.exit_stack.aclose()


def main() -> None:
    if len(sys.argv) < 2:
        logger.error("No server script path provided")
        logger.info("Usage: python client.py <path_to_server_script>")
        raise SystemExit(1)

    logger.info("Starting MCP client main loop with server %s", sys.argv[1])
    client = MCPClient()

    async def runner() -> None:
        try:
            await client.connect_to_server(sys.argv[1])
            await client.chat_loop()
        finally:
            await client.cleanup()
            logger.info("Client shutdown complete")

    asyncio.run(runner())


if __name__ == "__main__":
    main()
