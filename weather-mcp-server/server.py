from typing import Any
import httpx
from fastmcp import FastMCP
from starlette.datastructures import Headers
from starlette.responses import Response
from logger import get_logger

mcp = FastMCP(name="weather")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

log = get_logger("weather_mcp_server")

class AllowOptionsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            headers = Headers(scope=scope)
            origin = headers.get("origin", "*")
            allow_headers = headers.get("access-control-request-headers", "*")
            request_method = headers.get("access-control-request-method")
            if request_method:
                if request_method.upper() == "OPTIONS":
                    allow_methods = "OPTIONS"
                else:
                    allow_methods = f"{request_method}, OPTIONS"
            else:
                allow_methods = "GET, POST, DELETE, OPTIONS"

            response_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": allow_methods,
                "Access-Control-Allow-Headers": allow_headers,
            }

            response = Response(status_code=204, headers=response_headers)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

# Helper Functions
async def make_nws_request(url: str) -> dict[str, Any] | None:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            log.info(f"Request to {url} successful.")
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool(description="Get weather alerts for a US State")
async def get_alerts(state_abbreviated: str) -> str:
    """Get weather alerts for a US State

    Args:
        state_abbreviated: Two-letter US state code (eg. CA, NY)
    """
    if not state_abbreviated:
        message = "State must be provided as a US two-letter code (e.g. NY)."
        log.error(f"[get_alerts] Invalid state input: {state_abbreviated!r}")
        return message

    log.info(f"[get_alerts] State: {state_abbreviated} -> {state_abbreviated}")
    url = f"{NWS_API_BASE}/alerts/active/area/{state_abbreviated}"
    log.info(f"[get_alerts] URL: {url}")
    data = await make_nws_request(url)

    if data is None:
        log.info("No alerts data")
        return ""

    if not state_abbreviated or "features" not in data:
        log.error("No weather alerts data, missing state or feature")
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        log.error("No weather alerts data, missing features")
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool(description="Get weather alerts for location. Input in longitude and latitude")
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location (eg. 39.0997)
        longitude: Longitude of the location (eg. -94.5783)
    """
    log.info(f"[get_forecast] Latitude {latitude}, Longitude {longitude}")
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    log.info(f"Fetching weather forecast for {latitude}, {longitude}")
    points_data = await make_nws_request(points_url)

    if not points_data:
        log.error("No weather points data, missing points")
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        log.error("No weather forecast data, missing forecast")
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        log.info(f"Fetched forecast for period {period['name']}")
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


def main():
    # Initialize and run the server
    log.info("Starting Weather MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
