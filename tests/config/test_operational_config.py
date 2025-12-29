"""Tests for OperationalConfig domain configuration."""

from ai_radio.config.operational import OperationalConfig


class TestOperationalConfigDefaults:
    """Tests for OperationalConfig default values."""

    def test_break_freshness_minutes_default(self):
        """break_freshness_minutes should default to 50."""
        config = OperationalConfig()
        assert config.break_freshness_minutes == 50


class TestOperationalConfigEnvironment:
    """Tests for OperationalConfig environment variable overrides."""

    def test_break_freshness_minutes_from_env(self, monkeypatch):
        """break_freshness_minutes should load from RADIO_BREAK_FRESHNESS_MINUTES."""
        monkeypatch.setenv("RADIO_BREAK_FRESHNESS_MINUTES", "30")
        config = OperationalConfig()
        assert config.break_freshness_minutes == 30
