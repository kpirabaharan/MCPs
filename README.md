# Weather Tutorial

This repository contains a minimal client/server tutorial for working with weather data. It is intended as a starting point for experiments, workshops, or self-paced learning.

## Repository Layout

- `weather-mcp-client` – client-side project powering the user interface for the tutorial and automatically managing the server lifecycle when it runs.
- `weather-mcp-server` – standalone server project that exposes APIs used by the client and can also be explored independently.

## Getting Started (Client + Server)

1. Install the dependencies for both projects following the instructions in their respective directories.
2. Run the client; it will launch the server automatically, so you should not start the server manually when using the client.
3. Point the client at the server instance if prompted.

## Standalone Server in VS Code

1. Add the server directory to your VS Code workspace (`File` → `Add Folder to Workspace…` → select `weather-mcp-server`).
2. Install server dependencies (`uv venv && source .venv/bin/activate && uv sync`).
3. Update your MCP configuration (`mcp.json`) so VS Code (or the MCP extension) can spawn the server:
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
   - Use an absolute `cwd` so the extension resolves the script reliably.
   - Adjust `command`/`args` if you prefer a different launch method (e.g. `python server.py`).
4. Reload VS Code or the MCP extension so it picks up the updated configuration, then use the MCP panel to connect to the `weather` server for manual testing.

## Contributing

Feel free to open issues or submit pull requests with improvements, bug fixes, or suggestions for additional tutorial steps. Please keep changes well-scoped and include any relevant tests or documentation updates.

## License

This project is provided as-is for educational purposes. Adapt and extend it to suit your needs.
