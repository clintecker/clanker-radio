"""Tests for world-building and setting configuration."""

from ai_radio.config.world_building import WorldBuildingConfig


class TestWorldBuildingConfigDefaults:
    """Test default values for world-building configuration."""

    def test_world_setting_default(self):
        """Test world_setting has correct default value."""
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_setting == "laid-back tropical island paradise"

    def test_world_tone_default(self):
        """Test world_tone has correct default value."""
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_tone == "relaxed, friendly, warm, good vibes only, island time"

    def test_world_framing_default(self):
        """Test world_framing has correct default value."""
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_framing == "Broadcasting from our little slice of paradise. The news and weather filtered through the lens of island living - warm sun, cool breezes, and the sound of waves. We keep it real but keep it chill."


class TestWorldBuildingConfigEnvironment:
    """Test environment variable overrides for world-building configuration."""

    def test_world_setting_from_env(self, monkeypatch):
        """Test world_setting can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_WORLD_SETTING", "cyberpunk megacity")
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_setting == "cyberpunk megacity"

    def test_world_tone_from_env(self, monkeypatch):
        """Test world_tone can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_WORLD_TONE", "gritty, fast-paced, neon nights")
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_tone == "gritty, fast-paced, neon nights"

    def test_world_framing_from_env(self, monkeypatch):
        """Test world_framing can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_WORLD_FRAMING", "From the heart of the megacity...")
        config = WorldBuildingConfig(_env_file=None)
        assert config.world_framing == "From the heart of the megacity..."
