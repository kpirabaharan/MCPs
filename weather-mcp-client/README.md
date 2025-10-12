# Weather MCP Client

A terminal-based MCP client that lets a locally hosted OpenAI-compatible model call into the companion Weather MCP server. It follows the official [Model Context Protocol client tutorial](https://modelcontextprotocol.io/docs/develop/build-client) but targets any endpoint (Ollama, DeepSeek, etc.) that implements the OpenAI chat completions API.

## Prerequisites

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/latest/) for virtual environments and dependency management
- A running MCP server (for example `../weather-mcp-server/server.py` from this repo)
- A reachable OpenAI-compatible HTTP endpoint (for example, an Ollama or DeepSeek deployment)

## Setup

```bash
# inside weather-mcp-client/
uv venv
source .venv/bin/activate
uv sync
```

Create a `.env` file with your model endpoint details. Only the following variables are read by the client:

```bash
cat <<'ENV' > .env
API_BASE=http://localhost:8000/v1
MODEL=llama3.1:8b
API_KEY=not-required   # optional if your endpoint is open
```

`API_BASE` should point at the root of the OpenAI-compatible API. Omit `API_KEY` if your local server does not require authentication. `MODEL` defaults to `llama3.1:8b` when unset.

## Usage

1. Activate the virtual environment: `source .venv/bin/activate`
2. Launch the client and point it at an MCP server script:
   ```bash
   uv run client.py ../weather-mcp-server/server.py
   ```
3. Type natural-language questions. The backing model decides when to call MCP tools and streams responses back to the terminal.
4. Enter `quit` (or `exit`) to close the session.

If you are testing without your own server, you can pass any MCP server path—`client.py` simply spawns the script with stdio transport and relays tool definitions to the model.

## Configuration reference

| Variable | Purpose |
|----------|---------|
| `API_BASE` | Base URL for your OpenAI-compatible endpoint. |
| `API_KEY` | API key or token for the endpoint. Optional for unauthenticated local setups. |
| `MODEL` | Model name to request (defaults to `llama3.1:8b`). |

Any other runtime tweaks must be applied directly in `client.py`; no additional environment variables are consumed.

## Debugging tips

- Tool schemas flow straight from the MCP server into the chat completion request using OpenAI function-calling. Add breakpoints or print statements around `client.py`'s tool-handling code if you need to inspect the payloads.
- Tool outputs are flattened into text by `_flatten_tool_content`. Adjust that helper if your server returns rich content such as images or files.
- Logs are emitted via the shared `logger/` helpers and also stored under `logs/` when enabled.
