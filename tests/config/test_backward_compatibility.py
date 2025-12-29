"""Tests for backward compatibility property shims."""
import warnings
import pytest
from ai_radio.config.base import RadioConfig


class TestBackwardCompatibility:
    """Tests for deprecated property shims."""

    def test_station_name_shim_warns(self):
        """config.station_name should work with deprecation warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="station_name.*deprecated"):
            name = config.station_name

        assert name == config.station.station_name

    def test_base_path_shim_warns(self):
        """config.base_path should work with deprecation warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="base_path.*deprecated"):
            path = config.base_path

        assert path == config.paths.base_path

    def test_break_freshness_minutes_shim_warns(self):
        """config.break_freshness_minutes should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="break_freshness_minutes.*deprecated"):
            minutes = config.break_freshness_minutes

        assert minutes == config.operational.break_freshness_minutes

    def test_llm_api_key_shim_warns(self):
        """config.llm_api_key should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="llm_api_key.*deprecated"):
            key = config.llm_api_key

        # Shim returns plain string, domain config has SecretStr
        expected = config.api_keys.llm_api_key.get_secret_value() if config.api_keys.llm_api_key else None
        assert key == expected

    def test_announcer_name_shim_warns(self):
        """config.announcer_name should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="announcer_name.*deprecated"):
            name = config.announcer_name

        assert name == config.announcer.announcer_name

    def test_multiple_shims_work(self):
        """Multiple deprecated properties should all work."""
        config = RadioConfig()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            _ = config.station_name
            _ = config.base_path
            _ = config.break_freshness_minutes

            # Should have 3 warnings
            assert len(w) == 3
            assert all(issubclass(warning.category, DeprecationWarning) for warning in w)
