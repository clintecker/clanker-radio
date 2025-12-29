"""Configuration package for AI Radio Station.

This package provides domain-specific configuration modules
that replace the monolithic config.py.

Usage:
    from ai_radio.config import config, RadioConfig

    # Access domain configs
    config.paths.base_path
    config.api_keys.llm_api_key
    config.station.station_name
"""

from .base import RadioConfig
from .paths import PathsConfig
from .api_keys import APIKeysConfig
from .station_identity import StationIdentityConfig
from .announcer_personality import AnnouncerPersonalityConfig
from .world_building import WorldBuildingConfig
from .content_sources import ContentSourcesConfig
from .tts import TTSConfig
from .audio_mixing import AudioMixingConfig
from .operational import OperationalConfig

# Global singleton (backward compatibility)
config = RadioConfig()

__all__ = [
    "config",
    "RadioConfig",
    "PathsConfig",
    "APIKeysConfig",
    "StationIdentityConfig",
    "AnnouncerPersonalityConfig",
    "WorldBuildingConfig",
    "ContentSourcesConfig",
    "TTSConfig",
    "AudioMixingConfig",
    "OperationalConfig",
]
