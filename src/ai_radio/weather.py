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
class ForecastPeriod:
    """Single forecast period (e.g., 'This Afternoon', 'Tonight')."""

    name: str  # Period name
    temperature: int  # Fahrenheit
    conditions: str  # Short forecast
    detailed: str  # Detailed forecast text
    wind_speed: str  # Wind description
    precip_chance: Optional[int]  # Precipitation probability %


@dataclass
class HourlyForecast:
    """Single hour of forecast data."""

    time: datetime
    temperature: int
    conditions: str
    wind_speed: int  # mph
    precip_chance: int  # %


@dataclass
class WeatherData:
    """Comprehensive weather information for bulletin generation."""

    # Current conditions
    temperature: int  # Fahrenheit
    conditions: str  # Short description (e.g., "Partly Cloudy")

    # Extended forecasts
    current_period: ForecastPeriod  # Current period detailed info
    upcoming_periods: list[ForecastPeriod]  # Next 6 periods (tonight, tomorrow, etc.)
    hourly_forecast: list[HourlyForecast]  # Next 12 hours

    # Computed insights
    temp_trend: str  # e.g., "dropping 15° by evening", "warming up tomorrow"
    notable_events: list[str]  # e.g., ["Snow starts 6pm", "Freeze warning overnight"]
    travel_impact: Optional[str]  # Travel conditions summary

    timestamp: datetime


class NWSWeatherClient:
    """National Weather Service API client.

    Fetches comprehensive weather data from NWS grid endpoints.
    Implements NWS API guidelines: HTTPS, User-Agent, error handling.
    """

    BASE_URL = "https://api.weather.gov"
    USER_AGENT = "AIRadioStation/1.0 (+https://github.com/your-username/ai-radio-station)"

    def __init__(self):
        """Initialize NWS client with station configuration."""
        self.office = config.nws_office
        self.grid_x = config.nws_grid_x
        self.grid_y = config.nws_grid_y
        self.timeout = 10.0

    def _fetch_periods(self, client: httpx.Client) -> Optional[list[dict]]:
        """Fetch standard forecast periods."""
        forecast_url = (
            f"{self.BASE_URL}/gridpoints/{self.office}/"
            f"{self.grid_x},{self.grid_y}/forecast"
        )

        logger.info(f"Fetching NWS forecast periods")
        response = client.get(forecast_url, headers={"User-Agent": self.USER_AGENT})
        response.raise_for_status()
        data = response.json()
        return data["properties"]["periods"]

    def _fetch_hourly(self, client: httpx.Client) -> Optional[list[dict]]:
        """Fetch hourly forecast data."""
        hourly_url = (
            f"{self.BASE_URL}/gridpoints/{self.office}/"
            f"{self.grid_x},{self.grid_y}/forecast/hourly"
        )

        logger.info(f"Fetching NWS hourly forecast")
        response = client.get(hourly_url, headers={"User-Agent": self.USER_AGENT})
        response.raise_for_status()
        data = response.json()
        return data["properties"]["periods"]

    def _analyze_temp_trend(self, hourly: list[HourlyForecast]) -> str:
        """Analyze temperature trend over next 12 hours."""
        if len(hourly) < 2:
            return ""

        current_temp = hourly[0].temperature
        temps = [h.temperature for h in hourly[:12]]
        max_temp = max(temps)
        min_temp = min(temps)
        end_temp = hourly[min(11, len(hourly) - 1)].temperature

        temp_change = end_temp - current_temp

        if abs(temp_change) >= 10:
            direction = "dropping" if temp_change < 0 else "climbing"
            return f"{direction} {abs(temp_change)}° over next 12 hours"
        elif max_temp - min_temp >= 15:
            return f"swinging between {min_temp}° and {max_temp}° today"
        return ""

    def _find_notable_events(
        self, periods: list[ForecastPeriod], hourly: list[HourlyForecast]
    ) -> list[str]:
        """Identify notable weather events with timing."""
        events = []

        # Check for precipitation timing in hourly
        precip_start = None
        for i, h in enumerate(hourly[:12]):
            if h.precip_chance >= 40 and (i == 0 or hourly[i - 1].precip_chance < 40):
                precip_start = h.time
                break

        if precip_start:
            hour_str = precip_start.strftime("%-I%p").lower()
            events.append(f"Rain/snow likely starting around {hour_str}")

        # Check for significant wind
        high_wind = any(h.wind_speed >= 20 for h in hourly[:12])
        if high_wind:
            events.append("High winds expected (20+ mph)")

        # Check for freeze warning
        if any(h.temperature <= 32 for h in hourly[:12]):
            events.append("Temperatures at or below freezing")

        # Check for extreme temps
        temps = [h.temperature for h in hourly[:12]]
        if max(temps) >= 95:
            events.append("Extreme heat")
        elif min(temps) <= 10:
            events.append("Extreme cold")

        return events

    def _assess_travel_impact(
        self, periods: list[ForecastPeriod], hourly: list[HourlyForecast]
    ) -> Optional[str]:
        """Assess travel conditions."""
        # Check for conditions that impact travel
        has_precip = any(h.precip_chance >= 50 for h in hourly[:6])
        has_freeze = any(h.temperature <= 32 for h in hourly[:6])
        has_wind = any(h.wind_speed >= 25 for h in hourly[:6])

        if has_precip and has_freeze:
            return "Icy conditions likely - roads may be slippery"
        elif has_precip and has_wind:
            return "Poor visibility with wind and precipitation"
        elif has_wind:
            return "Gusty winds may affect high-profile vehicles"
        elif has_precip:
            return "Wet roads - allow extra travel time"

        return None

    def fetch_current_weather(self) -> Optional[WeatherData]:
        """Fetch comprehensive weather data with analysis.

        Returns:
            WeatherData with current conditions, forecasts, and insights.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Fetch both period and hourly forecasts
                periods_raw = self._fetch_periods(client)
                hourly_raw = self._fetch_hourly(client)

                if not periods_raw or not hourly_raw:
                    logger.error("NWS API returned no forecast data")
                    return None

                # Parse periods (current + next 6)
                current_period_raw = periods_raw[0]
                current_period = ForecastPeriod(
                    name=current_period_raw["name"],
                    temperature=current_period_raw["temperature"],
                    conditions=current_period_raw["shortForecast"],
                    detailed=current_period_raw["detailedForecast"],
                    wind_speed=current_period_raw.get("windSpeed", ""),
                    precip_chance=current_period_raw.get("probabilityOfPrecipitation", {}).get("value"),
                )

                upcoming_periods = []
                for p in periods_raw[1:7]:  # Next 6 periods
                    upcoming_periods.append(
                        ForecastPeriod(
                            name=p["name"],
                            temperature=p["temperature"],
                            conditions=p["shortForecast"],
                            detailed=p["detailedForecast"],
                            wind_speed=p.get("windSpeed", ""),
                            precip_chance=p.get("probabilityOfPrecipitation", {}).get("value"),
                        )
                    )

                # Parse hourly (next 12 hours)
                hourly_forecast = []
                for h in hourly_raw[:12]:
                    hourly_forecast.append(
                        HourlyForecast(
                            time=datetime.fromisoformat(h["startTime"].replace("Z", "+00:00")),
                            temperature=h["temperature"],
                            conditions=h["shortForecast"],
                            wind_speed=int(h.get("windSpeed", "0 mph").split()[0]),
                            precip_chance=h.get("probabilityOfPrecipitation", {}).get("value", 0) or 0,
                        )
                    )

                # Compute insights
                temp_trend = self._analyze_temp_trend(hourly_forecast)
                notable_events = self._find_notable_events(upcoming_periods, hourly_forecast)
                travel_impact = self._assess_travel_impact(upcoming_periods, hourly_forecast)

                weather = WeatherData(
                    temperature=current_period.temperature,
                    conditions=current_period.conditions,
                    current_period=current_period,
                    upcoming_periods=upcoming_periods,
                    hourly_forecast=hourly_forecast,
                    temp_trend=temp_trend,
                    notable_events=notable_events,
                    travel_impact=travel_impact,
                    timestamp=datetime.now(),
                )

                logger.info(
                    f"Weather fetched: {weather.temperature}°F, {weather.conditions}, "
                    f"{len(notable_events)} notable events"
                )
                return weather

        except httpx.HTTPError as e:
            logger.error(f"NWS API request failed: {e}")
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"NWS API response parsing failed: {e}")
            return None


def get_weather() -> Optional[WeatherData]:
    """Convenience function to fetch current weather.

    Returns:
        WeatherData or None if fetch fails.
    """
    client = NWSWeatherClient()
    return client.fetch_current_weather()
