# Weather Tutorial

This repository contains a minimal client/server tutorial for working with weather data. It is intended as a starting point for experiments, workshops, or self-paced learning.

## Repository Layout

- `weather-mcp-client` – client-side project powering the user interface for the tutorial and automatically managing the server lifecycle when it runs.
- `weather-mcp-server` – standalone server project that exposes APIs used by the client and can also be explored independently.

## Getting Started (Client + Server)

1. Install the dependencies for both projects following the instructions in their respective directories.
2. Decide how you want the client to reach the server (stdio vs. HTTP) and follow the steps below.
3. Point the client at the server instance if prompted.

## Running the MCP Client

- **STDIO (single process)**
  - Activate the client virtual environment (`cd weather-mcp-client && source .venv/bin/activate`).
  - Launch the client with the server path: `uv run client.py ../weather-mcp-server/server.py`.
  - The client will spawn the server over stdio, so you do **not** need to start the server separately in this mode.

- **HTTP (separate server process)**
  - Activate the server environment (`cd weather-mcp-server && source .venv/bin/activate`).
  - Start the server in HTTP mode, for example: `fastmcp run server.py:mcp --transport http --port 8000` (or adjust the command to your preferred runner/port).
  - Alternatively, build the Docker image in `weather-mcp-server/` (it defaults to stdio; pass `--transport http ...` after the image name to host over HTTP).
  - In a second shell, activate the client environment and run: `uv run client.py http://localhost:8000/mcp` (set `MCP_HTTP_HEADERS` if your server requires auth headers).
  - Because HTTP transport expects an already running server, confirm the server process is healthy before starting the client.

## Standalone Server in VS Code

1. Add the server directory to your VS Code workspace (`File` → `Add Folder to Workspace…` → select `weather-mcp-server`).
2. Install server dependencies (`uv venv && source .venv/bin/activate && uv sync`).
3. Update your MCP configuration (`mcp.json`) so VS Code (or the MCP extension) can spawn the server:

   a) Launch with `uv` (default):
      ```json
      {
        "servers": {
          "weather": {
            "command": "uv",
            "args": ["run", "server.py"],
            "cwd": "/absolute/path/to/weather-tutorial/weather-mcp-server"
          }
        }
      }
      ```
      Use an absolute `cwd` so the extension resolves the script reliably, and adjust `command`/`args` if you prefer a different launch method (for example `python server.py`).

   b) Launch with Docker:
      ```json
      {
        "servers": {
          "weather": {
            "command": "docker",
            "args": ["run", "--rm", "-i", "weather-mcp-server"],
            "cwd": "/absolute/path/to/weather-tutorial/weather-mcp-server"
          }
        }
      }
      ```
      Build the image in `weather-mcp-server/` (`docker build -t weather-mcp-server .`), and append extra flags to `args` (for example `"-p", "8000:8000", "--", "--transport", "http", "--port", "8000"`) if you need the HTTP transport instead of stdio.
4. Reload VS Code or the MCP extension so it picks up the updated configuration, then use the MCP panel to connect to the `weather` server for manual testing.

## Contributing

Feel free to open issues or submit pull requests with improvements, bug fixes, or suggestions for additional tutorial steps. Please keep changes well-scoped and include any relevant tests or documentation updates.

## License

This project is provided as-is for educational purposes. Adapt and extend it to suit your needs.
