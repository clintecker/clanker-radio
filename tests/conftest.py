"""Shared test fixtures and utilities for all tests."""

from datetime import datetime

from ai_radio.weather import WeatherData, ForecastPeriod, HourlyForecast


def create_test_weather_data(temperature=70, conditions="Sunny"):
    """Create test WeatherData with proper structure.

    This helper creates a properly structured WeatherData object
    with all required fields for testing purposes.
    """
    current_period = ForecastPeriod(
        name="This Afternoon",
        temperature=temperature,
        conditions=conditions,
        detailed="Test forecast details",
        wind_speed="5 mph",
        precip_chance=10,
    )

    upcoming_period = ForecastPeriod(
        name="Tonight",
        temperature=temperature - 10,
        conditions="Clear",
        detailed="Clear skies overnight",
        wind_speed="3 mph",
        precip_chance=0,
    )

    hourly = HourlyForecast(
        time=datetime.now(),
        temperature=temperature,
        conditions=conditions,
        wind_speed=5,
        precip_chance=10,
    )

    return WeatherData(
        temperature=temperature,
        conditions=conditions,
        current_period=current_period,
        upcoming_periods=[upcoming_period],
        hourly_forecast=[hourly],
        temp_trend="steady",
        notable_events=[],
        travel_impact=None,
        timestamp=datetime.now(),
    )
