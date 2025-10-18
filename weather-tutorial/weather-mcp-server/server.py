from typing import Any
import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from logger import get_logger

mcp = FastMCP(name="weather")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

log = get_logger("weather_mcp_server")


class WeatherAlert(BaseModel):
    event: str = Field(
        ..., description="Name of the weather event, e.g. Tornado Warning"
    )
    area: str = Field(..., description="Areas affected by the alert")
    severity: str | None = Field(None, description="Relative severity provided by NWS")
    description: str | None = Field(
        None, description="Full description text from the alert"
    )
    instructions: str | None = Field(
        None, description="Recommended actions or instructions"
    )


class WeatherData(BaseModel):
    period: str = Field(..., description="Label for the forecast period, e.g. Tonight")
    temperature: float | None = Field(
        None, description="Temperature value in degrees Celsius"
    )
    temperature_unit: str | None = Field(
        "C",
        description="Unit for the reported temperature (always Celsius when provided)",
    )
    wind_speed: str | None = Field(
        None, description="Reported wind speed, e.g. 5 to 10 mph"
    )
    wind_direction: str | None = Field(
        None, description="Compass direction the wind is coming from"
    )
    detailed_forecast: str = Field(
        ..., description="Full forecast narrative for the period"
    )


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


@mcp.prompt(title="Get weather alerts for a US State")
def prompt_get_alerts(state_abbreviated: str) -> str:
    return f"Get weather alerts for the US state with the two-letter code '{state_abbreviated}'."


@mcp.tool(description="Get weather alerts for a US State")
async def get_alerts(state_abbreviated: str) -> list[WeatherAlert]:
    """Get weather alerts for a US State

    Args:
        state_abbreviated: Two-letter US state code (eg. CA, NY)
    """
    if not state_abbreviated:
        log.error(f"[get_alerts] Invalid state input: {state_abbreviated!r}")
        return []

    log.info(f"[get_alerts] State: {state_abbreviated} -> {state_abbreviated}")
    url = f"{NWS_API_BASE}/alerts/active/area/{state_abbreviated}"
    log.info(f"[get_alerts] URL: {url}")
    data = await make_nws_request(url)

    if data is None:
        log.info("No alerts data")
        return []

    features = data.get("features", [])
    if not features:
        log.error("No weather alerts data, missing features")
        return []

    alerts: list[WeatherAlert] = []
    for feature in features:
        props = feature.get("properties", {})
        alerts.append(
            WeatherAlert(
                event=props.get("event") or "Unknown",
                area=props.get("areaDesc") or "Unknown",
                severity=props.get("severity"),
                description=props.get("description"),
                instructions=props.get("instruction"),
            )
        )

    return alerts


@mcp.tool(
    description="Get weather alerts for location. Input in longitude and latitude"
)
async def get_forecast(latitude: float, longitude: float) -> list[WeatherData]:
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
        return []

    # Get the forecast URL from the points response
    forecast_url = points_data.get("properties", {}).get("forecast")
    if not forecast_url:
        log.error("No forecast URL found in points data")
        return []
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        log.error("No weather forecast data, missing forecast")
        return []

    # Format the periods into a readable forecast
    periods = forecast_data.get("properties", {}).get("periods", [])
    forecasts: list[WeatherData] = []
    for period in periods[:5]:  # Only show next 5 periods
        log.info(f"Fetched forecast for period {period.get('name')}")

        raw_temperature = period.get("temperature")
        raw_unit = (period.get("temperatureUnit") or "").upper()
        celsius_temperature: float | None = None
        if raw_temperature is not None:
            try:
                numeric_temp = float(raw_temperature)
            except (TypeError, ValueError):
                celsius_temperature = None
            else:
                if raw_unit == "C":
                    celsius_temperature = numeric_temp
                else:
                    celsius_temperature = (numeric_temp - 32.0) * 5.0 / 9.0

        forecasts.append(
            WeatherData(
                period=period.get("name") or "Unknown",
                temperature=(
                    round(celsius_temperature, 2)
                    if celsius_temperature is not None
                    else None
                ),
                temperature_unit="C" if celsius_temperature is not None else None,
                wind_speed=period.get("windSpeed"),
                wind_direction=period.get("windDirection"),
                detailed_forecast=period.get("detailedForecast") or "",
            )
        )

    return forecasts


def main():
    # Initialize and run the server
    log.info("Starting Weather MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
