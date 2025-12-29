"""Tests for NWS weather API client.

Test coverage:
- Successful weather fetching
- HTTP error handling
- Response parsing error handling
- Empty periods handling
"""

from datetime import datetime
from unittest.mock import Mock, patch

import httpx
import pytest

from ai_radio.weather import NWSWeatherClient, WeatherData, get_weather
from conftest import create_test_weather_data


class TestNWSWeatherClient:
    """Tests for NWSWeatherClient."""

    def test_initialization_uses_config(self):
        """NWSWeatherClient should load office and grid from config."""
        with patch("ai_radio.weather.config") as mock_config:
            mock_config.nws_office = "LOT"
            mock_config.nws_grid_x = 76
            mock_config.nws_grid_y = 73

            client = NWSWeatherClient()

            assert client.office == "LOT"
            assert client.grid_x == 76
            assert client.grid_y == 73
            assert client.timeout == 10.0

    def test_fetch_current_weather_success(self):
        """fetch_current_weather should return WeatherData on successful API call."""
        with patch("ai_radio.weather.config") as mock_config:
            mock_config.nws_office = "LOT"
            mock_config.nws_grid_x = 76
            mock_config.nws_grid_y = 73

            client = NWSWeatherClient()

            mock_periods_response = {
                "properties": {
                    "periods": [
                        {
                            "name": "This Afternoon",
                            "temperature": 72,
                            "shortForecast": "Partly Cloudy",
                            "detailedForecast": "Partly cloudy with a high near 72. Southwest wind 5 to 10 mph.",
                            "windSpeed": "5 to 10 mph",
                            "probabilityOfPrecipitation": {"value": 10}
                        },
                        {
                            "name": "Tonight",
                            "temperature": 60,
                            "shortForecast": "Clear",
                            "detailedForecast": "Clear skies overnight.",
                            "windSpeed": "3 mph",
                            "probabilityOfPrecipitation": {"value": 0}
                        }
                    ]
                }
            }

            mock_hourly_response = {
                "properties": {
                    "periods": [
                        {
                            "startTime": "2024-01-01T12:00:00Z",
                            "temperature": 72,
                            "shortForecast": "Partly Cloudy",
                            "windSpeed": "5 mph",
                            "probabilityOfPrecipitation": {"value": 10}
                        }
                    ]
                }
            }

            with patch("httpx.Client") as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value.__enter__.return_value = mock_client

                # Mock two calls: periods first, then hourly
                mock_periods_resp = Mock()
                mock_periods_resp.json.return_value = mock_periods_response
                mock_hourly_resp = Mock()
                mock_hourly_resp.json.return_value = mock_hourly_response

                mock_client.get.side_effect = [mock_periods_resp, mock_hourly_resp]

                weather = client.fetch_current_weather()

                # Verify both API calls were made
                assert mock_client.get.call_count == 2
                first_call = mock_client.get.call_args_list[0]
                assert "User-Agent" in first_call[1]["headers"]
                assert "gridpoints/LOT/76,73/forecast" in first_call[0][0]

                # Verify returned data
                assert weather is not None
                assert weather.temperature == 72
                assert weather.conditions == "Partly Cloudy"
                assert isinstance(weather.timestamp, datetime)

    def test_fetch_current_weather_http_error(self):
        """fetch_current_weather should return None on HTTP error."""
        client = NWSWeatherClient()

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_client.get.side_effect = httpx.HTTPError("Network error")

            weather = client.fetch_current_weather()

            assert weather is None

    def test_fetch_current_weather_http_status_error(self):
        """fetch_current_weather should return None on HTTP status error."""
        client = NWSWeatherClient()

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=Mock(status_code=404),
            )
            mock_client.get.return_value = mock_response

            weather = client.fetch_current_weather()

            assert weather is None

    def test_fetch_current_weather_empty_periods(self):
        """fetch_current_weather should return None when API returns no periods."""
        client = NWSWeatherClient()

        mock_response = {"properties": {"periods": []}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.json.return_value = mock_response
            mock_client.get.return_value = mock_get_response

            weather = client.fetch_current_weather()

            assert weather is None

    def test_fetch_current_weather_malformed_response(self):
        """fetch_current_weather should return None on malformed JSON structure."""
        client = NWSWeatherClient()

        mock_response = {"properties": {"wrong_key": []}}

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.json.return_value = mock_response
            mock_client.get.return_value = mock_get_response

            weather = client.fetch_current_weather()

            assert weather is None

    def test_forecast_truncation(self):
        """fetch_current_weather should handle long detailed forecasts."""
        client = NWSWeatherClient()

        long_forecast = "A" * 500  # 500 character forecast

        mock_periods_response = {
            "properties": {
                "periods": [
                    {
                        "name": "This Afternoon",
                        "temperature": 68,
                        "shortForecast": "Sunny",
                        "detailedForecast": long_forecast,
                        "windSpeed": "5 mph",
                        "probabilityOfPrecipitation": {"value": 10}
                    }
                ]
            }
        }

        mock_hourly_response = {
            "properties": {
                "periods": [
                    {
                        "startTime": "2024-01-01T12:00:00Z",
                        "temperature": 68,
                        "shortForecast": "Sunny",
                        "windSpeed": "5 mph",
                        "probabilityOfPrecipitation": {"value": 10}
                    }
                ]
            }
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_periods_resp = Mock()
            mock_periods_resp.json.return_value = mock_periods_response
            mock_hourly_resp = Mock()
            mock_hourly_resp.json.return_value = mock_hourly_response

            mock_client.get.side_effect = [mock_periods_resp, mock_hourly_resp]

            weather = client.fetch_current_weather()

            assert weather is not None
            assert weather.current_period.detailed == long_forecast
            assert len(weather.current_period.detailed) == 500


class TestGetWeatherConvenience:
    """Tests for get_weather() convenience function."""

    def test_get_weather_success(self):
        """get_weather should return WeatherData on success."""
        mock_weather = create_test_weather_data(temperature=75, conditions="Clear")

        with patch("ai_radio.weather.NWSWeatherClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_current_weather.return_value = mock_weather
            mock_client_class.return_value = mock_client

            result = get_weather()

            assert result == mock_weather

    def test_get_weather_failure(self):
        """get_weather should return None on fetch failure."""
        with patch("ai_radio.weather.NWSWeatherClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_current_weather.return_value = None
            mock_client_class.return_value = mock_client

            result = get_weather()

            assert result is None
