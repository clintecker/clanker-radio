"""Tests for StationIdentityConfig domain configuration."""


import pytest

from ai_radio.config.station_identity import StationIdentityConfig


class TestStationIdentityConfig:
    """Tests for StationIdentityConfig."""

    def test_default_station_name(self):
        """station_name should have default value."""
        station = StationIdentityConfig(_env_file=None)
        assert station.station_name == "WKRP Coconut Island"

    def test_station_name_from_env(self, monkeypatch):
        """station_name should load from RADIO_STATION_NAME env var."""
        monkeypatch.setenv("RADIO_STATION_NAME", "Test Radio")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_name == "Test Radio"

    def test_default_station_location(self):
        """station_location should have default value."""
        station = StationIdentityConfig(_env_file=None)
        assert station.station_location == "Coconut Island"

    def test_station_location_from_env(self, monkeypatch):
        """station_location should load from RADIO_STATION_LOCATION env var."""
        monkeypatch.setenv("RADIO_STATION_LOCATION", "Test City")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_location == "Test City"

    def test_default_station_tz(self):
        """station_tz should have default value."""
        station = StationIdentityConfig(_env_file=None)
        assert station.station_tz == "Pacific/Honolulu"

    def test_station_tz_from_env(self, monkeypatch):
        """station_tz should load from RADIO_STATION_TZ env var."""
        monkeypatch.setenv("RADIO_STATION_TZ", "America/New_York")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_tz == "America/New_York"

    def test_default_station_lat_none(self):
        """station_lat should default to None."""
        station = StationIdentityConfig(_env_file=None)
        assert station.station_lat is None

    def test_station_lat_from_env(self, monkeypatch):
        """station_lat should load from RADIO_STATION_LAT env var."""
        monkeypatch.setenv("RADIO_STATION_LAT", "21.3099")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_lat == 21.3099

    def test_default_station_lon_none(self):
        """station_lon should default to None."""
        station = StationIdentityConfig(_env_file=None)
        assert station.station_lon is None

    def test_station_lon_from_env(self, monkeypatch):
        """station_lon should load from RADIO_STATION_LON env var."""
        monkeypatch.setenv("RADIO_STATION_LON", "-157.8581")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_lon == -157.8581

    def test_invalid_latitude_too_high(self, monkeypatch):
        """station_lat should reject values > 90."""
        monkeypatch.setenv("RADIO_STATION_LAT", "95.0")
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            StationIdentityConfig(_env_file=None)

    def test_invalid_latitude_too_low(self, monkeypatch):
        """station_lat should reject values < -90."""
        monkeypatch.setenv("RADIO_STATION_LAT", "-95.0")
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            StationIdentityConfig(_env_file=None)

    def test_invalid_longitude_too_high(self, monkeypatch):
        """station_lon should reject values > 180."""
        monkeypatch.setenv("RADIO_STATION_LON", "185.0")
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            StationIdentityConfig(_env_file=None)

    def test_invalid_longitude_too_low(self, monkeypatch):
        """station_lon should reject values < -180."""
        monkeypatch.setenv("RADIO_STATION_LON", "-185.0")
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            StationIdentityConfig(_env_file=None)

    def test_valid_coordinates(self, monkeypatch):
        """Valid lat/lon coordinates should be accepted."""
        monkeypatch.setenv("RADIO_STATION_LAT", "21.3099")
        monkeypatch.setenv("RADIO_STATION_LON", "-157.8581")
        station = StationIdentityConfig(_env_file=None)
        assert station.station_lat == 21.3099
        assert station.station_lon == -157.8581


class TestStationIdentityProductionValidation:
    """Tests for StationIdentityConfig production validation."""

    def test_validate_production_fails_without_coordinates(self):
        """validate_production should fail when coordinates missing."""
        # Create config with explicitly None coordinates to override .env file
        config = StationIdentityConfig(station_lat=None, station_lon=None)
        with pytest.raises(ValueError, match="RADIO_STATION_LAT"):
            config.validate_production()

    def test_validate_production_fails_without_lon(self):
        """validate_production should fail when longitude missing."""
        # Create config with explicit LAT but None LON to override .env file
        config = StationIdentityConfig(station_lat=21.3, station_lon=None)
        with pytest.raises(ValueError, match="RADIO_STATION_LON"):
            config.validate_production()

    def test_validate_production_succeeds_with_coordinates(self, monkeypatch):
        """validate_production should succeed with both coordinates."""
        monkeypatch.setenv("RADIO_STATION_LAT", "21.3")
        monkeypatch.setenv("RADIO_STATION_LON", "-157.8")
        config = StationIdentityConfig(_env_file=None)
        config.validate_production()  # Should not raise
