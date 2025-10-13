# Weather MCP Server

An MCP-compliant server that wraps the National Weather Service (NWS) API and exposes a pair of tools that clients can call over the Model Context Protocol. It is adapted from the official [weather MCP tutorial](https://modelcontextprotocol.io/docs/tutorials/weather) and runs on top of [`fastmcp`](https://github.com/radiantly/fastmcp).

## What it provides

- `get_alerts(state_abbreviated: str)`: returns active NWS alerts for the provided two-letter US state code.
- `get_forecast(latitude: float, longitude: float)`: returns the next few forecast periods for a latitude/longitude pair using the NWS gridpoints API.

Both tools format responses as plain text so MCP clients (like the companion DeepSeek client in this repo) can stream them directly to a user.

## Prerequisites

- Python 3.13+
- [`uv`](https://docs.astral.sh/uv/latest/) for virtualenv and dependency management
- Outbound HTTPS access to `https://api.weather.gov`

## Setup

```bash
# inside weather-mcp-server/
uv venv
source .venv/bin/activate
uv sync
```

The dependencies include `fastmcp`, `httpx`, and the reference `mcp` CLI.

## Running the server

The server defaults to the `stdio` transport so it is typically spawned by an MCP client. To manually exercise it during development you can use the MCP CLI inspector:

```bash
source .venv/bin/activate

# STDIO
fastmcp run server.py:mcp
# HTTP
fastmcp run server.py:mcp --transport http --port 8000

# DEV
# STDIO
fastmcp dev server.py
# HTTP


```

This opens an interactive shell where you can invoke `get_alerts` and `get_forecast` directly.

If you prefer to host the server over HTTP, flip the `mcp.run` call in `server.py` to `transport="http"` and choose a port. Clients can then connect via HTTP instead of stdio.

## Container image

Build the Docker image from this directory. The container defaults to the stdio transport, matching the non-container workflow:

```bash
# Build the image (tagged as weather-mcp-server)
docker build -t weather-mcp-server .

# Run with stdio (use -it so the pipes stay attached)
docker run --rm -it weather-mcp-server
```

To host the server over HTTP, append the desired flags after the image name when starting the container:

```bash
docker run --rm -p 8000:8000 weather-mcp-server \
  --transport http --host 0.0.0.0 --port 8000
```

The `.dockerignore` keeps local virtual environments, logs, and Git metadata out of the build context.

## Logging

Structured logs are written to stderr and also rotated daily in the `logs/` directory (e.g. `logs/weather_mcp_server_2025-01-01.log`). Adjust `logger/config.py` if you need a different logging format or destination.

## Project structure

- `server.py` – MCP tool definitions and startup entrypoint
- `logger/` – shared logging configuration used by the server
- `pyproject.toml` – Python project metadata and dependencies
- `logs/` – runtime log files (created on demand)

## Next steps

Pair this server with the client located in `../weather-mcp-client/` to let a local DeepSeek model fetch weather data through MCP tool calls.
