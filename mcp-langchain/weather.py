from typing import Any, List
import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from logger import get_logger
from env_canada import ECWeather

mcp = FastMCP(name="weather")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

log = get_logger("weather_mcp_server")


class WeatherData(BaseModel):
    period: str = Field(..., description="Label for the forecast period, e.g. Tonight")
    temperature: float | None = Field(
        None, description="Temperature value in degrees Celsius"
    )
    temperature_unit: str | None = Field(
        "C",
        description="Unit for the reported temperature (always Celsius when provided)",
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


async def make_can_request(
    latitude: float, longitude: float
) -> List[dict[str, Any]] | None:
    weather = ECWeather(coordinates=(latitude, longitude))

    try:
        await weather.update()
        return weather.daily_forecasts
    except Exception as e:
        log.error(f"Error fetching Canadian weather data: {e}")
        return None


@mcp.prompt(title="Forecast (US coordinates)", name="weather_us")
def prompt_forecast_us(latitude: float, longitude: float) -> str:
    return (
        "Use `weather.get_forecast_us` for this location.\n"
        f"- latitude: {latitude}\n"
        f"- longitude: {longitude}\n"
        "Concisely print today's temperature."
    )


@mcp.tool(
    description="Get weather alerts for a location in US. Input in longitude and latitude"
)
async def get_forecast_us(latitude: float, longitude: float) -> list[WeatherData]:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location (eg. 39.0997)
        longitude: Longitude of the location (eg. -94.5783)
    """
    log.info(f"[get_forecast] Latitude {latitude}, Longitude {longitude}")
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
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
                detailed_forecast=period.get("detailedForecast") or "",
            )
        )

    return forecasts


@mcp.tool(
    description="Get weather alerts for location in Canada. Input in longitude and latitude"
)
async def get_forecast_can(latitude: float, longitude: float) -> list[WeatherData]:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location (eg. 43.8611)
        longitude: Longitude of the location (eg. -79.0259)
    """
    log.info(f"[get_forecast_can] Latitude {latitude}, Longitude {longitude}")
    forecast_data = await make_can_request(latitude, longitude)

    if not forecast_data:
        log.error(f"No weather forecast data for {latitude}, {longitude}")
        return []

    forecasts: list[WeatherData] = []
    for period in forecast_data[:5]:
        period_name = period.get("period")
        log.info(f"Fetched forecast for period {period_name}")

        temperature = period.get("temperature")
        unit = "°C"

        forecasts.append(
            WeatherData(
                period=period_name,
                temperature=temperature,
                temperature_unit=unit,
                detailed_forecast=period.get("text_summary") or "",
            )
        )

    return forecasts


def main():
    # Initialize and run the server
    log.info("Starting Weather MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
