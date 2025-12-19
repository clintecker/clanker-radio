"""Weather data fetching from National Weather Service API.

Fetches current conditions and forecast from NWS grid endpoints.
Uses HTTPS with proper User-Agent per NWS API requirements.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Structured weather information for bulletin generation."""

    temperature: int  # Fahrenheit
    conditions: str  # Short description (e.g., "Partly Cloudy")
    forecast_short: str  # Short forecast text
    timestamp: datetime


class NWSWeatherClient:
    """National Weather Service API client.

    Fetches weather data from NWS grid endpoints for configured station location.
    Implements NWS API guidelines: HTTPS, User-Agent, error handling.
    """

    BASE_URL = "https://api.weather.gov"
    USER_AGENT = "AIRadioStation/1.0 (https://radio.clintecker.com)"

    def __init__(self):
        """Initialize NWS client with station configuration."""
        self.office = config.nws_office
        self.grid_x = config.nws_grid_x
        self.grid_y = config.nws_grid_y
        self.timeout = 10.0

    def fetch_current_weather(self) -> Optional[WeatherData]:
        """Fetch current weather conditions and forecast.

        Returns:
            WeatherData with current conditions and forecast, or None if fetch fails.

        Raises:
            httpx.HTTPError: If NWS API request fails
        """
        try:
            # Fetch gridpoint forecast
            forecast_url = (
                f"{self.BASE_URL}/gridpoints/{self.office}/"
                f"{self.grid_x},{self.grid_y}/forecast"
            )

            logger.info(f"Fetching NWS forecast from {forecast_url}")

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    forecast_url,
                    headers={"User-Agent": self.USER_AGENT},
                )
                response.raise_for_status()

                data = response.json()

                # Extract first period (current/today)
                periods = data["properties"]["periods"]
                if not periods:
                    logger.error("NWS API returned no forecast periods")
                    return None

                current_period = periods[0]

                weather = WeatherData(
                    temperature=current_period["temperature"],
                    conditions=current_period["shortForecast"],
                    forecast_short=current_period["detailedForecast"][:200],
                    timestamp=datetime.now(),
                )

                logger.info(
                    f"Weather fetched: {weather.temperature}°F, {weather.conditions}"
                )
                return weather

        except httpx.HTTPError as e:
            logger.error(f"NWS API request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"NWS API response parsing failed: {e}")
            return None


def get_weather() -> Optional[WeatherData]:
    """Convenience function to fetch current weather.

    Returns:
        WeatherData or None if fetch fails.
    """
    client = NWSWeatherClient()
    return client.fetch_current_weather()
