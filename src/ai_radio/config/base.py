"""Configuration composition root."""
import os
import warnings
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import PathsConfig
from .api_keys import APIKeysConfig
from .station_identity import StationIdentityConfig
from .announcer_personality import AnnouncerPersonalityConfig
from .world_building import WorldBuildingConfig
from .content_sources import ContentSourcesConfig
from .tts import TTSConfig
from .audio_mixing import AudioMixingConfig
from .operational import OperationalConfig


class RadioConfig(BaseSettings):
    """Root configuration composing all domain configs.

    Composes 9 domain-specific configs into a unified configuration.
    Maintains backward compatibility via property shims.
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows RADIO_API_KEYS__LLM_API_KEY
        case_sensitive=False,
        extra="ignore",
    )

    # Domain compositions (using default_factory to avoid mutable default bug)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    api_keys: APIKeysConfig = Field(default_factory=APIKeysConfig)
    station: StationIdentityConfig = Field(default_factory=StationIdentityConfig)
    announcer: AnnouncerPersonalityConfig = Field(default_factory=AnnouncerPersonalityConfig)
    world: WorldBuildingConfig = Field(default_factory=WorldBuildingConfig)
    content: ContentSourcesConfig = Field(default_factory=ContentSourcesConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    audio: AudioMixingConfig = Field(default_factory=AudioMixingConfig)
    operational: OperationalConfig = Field(default_factory=OperationalConfig)

    # Fields that don't fit cleanly in existing domains (YAGNI - don't create domains for 2-3 fields)
    llm_model: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Claude model for bulletin script generation"
    )
    weather_script_temperature: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Temperature for weather script generation (0.0=deterministic, 1.0=creative)"
    )
    news_script_temperature: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Temperature for news script generation (0.0=deterministic, 1.0=creative)"
    )

    # Icecast integration (external system, doesn't fit domain model)
    @property
    def icecast_url(self) -> str:
        """Icecast server URL."""
        return "http://localhost:8000"

    @property
    def icecast_admin_password(self) -> str:
        """Icecast admin password from environment or Icecast XML config."""
        # Try environment variable first
        password = os.getenv("ICECAST_ADMIN_PASSWORD")
        if password:
            return password

        # Read from Icecast XML config
        try:
            import xml.etree.ElementTree as ET
            icecast_config = Path("/etc/icecast2/icecast.xml")
            if icecast_config.exists():
                tree = ET.parse(icecast_config)
                root = tree.getroot()
                admin_pass_elem = root.find('.//authentication/admin-password')
                if admin_pass_elem is not None and admin_pass_elem.text:
                    return admin_pass_elem.text
        except Exception:
            pass

        # Fallback default (for development)
        return ""

    def validate_production_config(self) -> None:
        """Validate all domain production requirements.

        Raises:
            ValueError: If required production fields are missing
        """
        self.api_keys.validate_production()
        self.station.validate_production()

    # ===================================================================
    # Backward compatibility property shims (DEPRECATED)
    # Remove after all code migrated to new API
    # ===================================================================

    @property
    def station_name(self) -> str:
        """DEPRECATED: Use config.station.station_name instead."""
        warnings.warn(
            "'config.station_name' is deprecated. Use 'config.station.station_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.station.station_name

    @property
    def base_path(self) -> Path:
        """DEPRECATED: Use config.paths.base_path instead."""
        warnings.warn(
            "'config.base_path' is deprecated. Use 'config.paths.base_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.base_path

    @property
    def break_freshness_minutes(self) -> int:
        """DEPRECATED: Use config.operational.break_freshness_minutes instead."""
        warnings.warn(
            "'config.break_freshness_minutes' is deprecated. Use 'config.operational.break_freshness_minutes' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.operational.break_freshness_minutes

    @property
    def llm_api_key(self):
        """DEPRECATED: Use config.api_keys.llm_api_key instead."""
        warnings.warn(
            "'config.llm_api_key' is deprecated. Use 'config.api_keys.llm_api_key' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.api_keys.llm_api_key

    @property
    def announcer_name(self) -> str:
        """DEPRECATED: Use config.announcer.announcer_name instead."""
        warnings.warn(
            "'config.announcer_name' is deprecated. Use 'config.announcer.announcer_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.announcer_name

    # TODO: Add shims for all commonly accessed fields
    # Run `grep -r "config\." src/ scripts/` to find usages
