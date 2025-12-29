"""Tests for RadioConfig - composition root."""
import pytest
from ai_radio.config.base import RadioConfig
from ai_radio.config.paths import PathsConfig
from ai_radio.config.api_keys import APIKeysConfig
from ai_radio.config.station_identity import StationIdentityConfig
from ai_radio.config.announcer_personality import AnnouncerPersonalityConfig
from ai_radio.config.world_building import WorldBuildingConfig
from ai_radio.config.content_sources import ContentSourcesConfig
from ai_radio.config.tts import TTSConfig
from ai_radio.config.audio_mixing import AudioMixingConfig
from ai_radio.config.operational import OperationalConfig


class TestRadioConfigComposition:
    """Tests for RadioConfig composition."""

    def test_composes_all_domains(self):
        """RadioConfig should compose all 9 domain configs."""
        config = RadioConfig()

        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.api_keys, APIKeysConfig)
        assert isinstance(config.station, StationIdentityConfig)
        assert isinstance(config.announcer, AnnouncerPersonalityConfig)
        assert isinstance(config.world, WorldBuildingConfig)
        assert isinstance(config.content, ContentSourcesConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.audio, AudioMixingConfig)
        assert isinstance(config.operational, OperationalConfig)

    def test_default_factory_creates_new_instances(self):
        """Each RadioConfig should get fresh domain instances."""
        config1 = RadioConfig()
        config2 = RadioConfig()

        # Different instances
        assert config1.paths is not config2.paths
        assert config1.api_keys is not config2.api_keys

    def test_validate_production_config_calls_domains(self, monkeypatch):
        """validate_production_config should call all domain validations."""
        # Clear environment to ensure missing required fields
        monkeypatch.delenv("RADIO_LLM_API_KEY", raising=False)
        monkeypatch.delenv("RADIO_TTS_API_KEY", raising=False)

        config = RadioConfig()

        with pytest.raises(ValueError) as exc_info:
            config.validate_production_config()

        # Should mention missing LLM and TTS keys
        error_msg = str(exc_info.value)
        assert "LLM_API_KEY" in error_msg or "TTS_API_KEY" in error_msg

    def test_validate_production_config_succeeds(self, monkeypatch):
        """validate_production_config should succeed with all required fields."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-llm")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-tts")
        monkeypatch.setenv("RADIO_STATION_LAT", "21.3")
        monkeypatch.setenv("RADIO_STATION_LON", "-157.8")

        config = RadioConfig()
        config.validate_production_config()  # Should not raise

    def test_llm_model_field_exists(self):
        """RadioConfig should have llm_model field (doesn't fit domain model)."""
        config = RadioConfig()
        assert config.llm_model == "claude-3-5-sonnet-latest"

    def test_script_temperature_fields_exist(self):
        """RadioConfig should have temperature fields."""
        config = RadioConfig()
        assert config.weather_script_temperature == 0.8
        assert config.news_script_temperature == 0.6

    def test_icecast_properties_exist(self):
        """RadioConfig should have icecast properties."""
        config = RadioConfig()
        assert config.icecast_url == "http://localhost:8000"
        assert isinstance(config.icecast_admin_password, str)


class TestConfigPackageExports:
    """Tests for config package __init__.py exports."""

    def test_config_singleton_exists(self):
        """config package should export config singleton."""
        from ai_radio.config import config
        assert config is not None
        assert isinstance(config, RadioConfig)

    def test_radioconfig_class_exported(self):
        """config package should export RadioConfig class."""
        from ai_radio.config import RadioConfig as ExportedRadioConfig
        assert ExportedRadioConfig is RadioConfig

    def test_all_domain_configs_exported(self):
        """config package should export all domain config classes."""
        from ai_radio.config import (
            PathsConfig,
            APIKeysConfig,
            StationIdentityConfig,
            AnnouncerPersonalityConfig,
            WorldBuildingConfig,
            ContentSourcesConfig,
            TTSConfig,
            AudioMixingConfig,
            OperationalConfig,
        )

        # All should be classes
        assert PathsConfig is not None
        assert APIKeysConfig is not None
        assert StationIdentityConfig is not None
        assert AnnouncerPersonalityConfig is not None
        assert WorldBuildingConfig is not None
        assert ContentSourcesConfig is not None
        assert TTSConfig is not None
        assert AudioMixingConfig is not None
        assert OperationalConfig is not None
