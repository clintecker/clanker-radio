"""Configuration management for AI Radio Station.

Uses pydantic-settings for environment-based configuration with sensible defaults.
All paths and secrets can be overridden via environment variables.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RadioConfig(BaseSettings):
    """AI Radio Station configuration.

    Environment variables:
        RADIO_BASE_PATH: Base directory (default: /srv/ai_radio)
        RADIO_STATION_TZ: IANA timezone (default: America/Chicago)
        RADIO_STATION_LAT: Station latitude for weather
        RADIO_STATION_LON: Station longitude for weather
        RADIO_LLM_API_KEY: LLM provider API key
        RADIO_TTS_API_KEY: TTS provider API key
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file="/srv/ai_radio/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base paths
    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Station configuration
    station_tz: str = Field(default="America/Chicago")
    station_lat: Optional[float] = Field(default=None)
    station_lon: Optional[float] = Field(default=None)

    # API keys (required for production, optional for testing)
    llm_api_key: Optional[str] = Field(default=None)
    tts_api_key: Optional[str] = Field(default=None)

    # Phase 4: Content Generation Settings
    nws_office: str = Field(default="LOT", description="NWS office code (Chicago)")
    nws_grid_x: int = Field(default=76, description="NWS grid X coordinate")
    nws_grid_y: int = Field(default=73, description="NWS grid Y coordinate")

    news_rss_feeds: list[str] = Field(
        default=[
            "https://feeds.npr.org/1001/rss.xml",
            "https://www.chicagotribune.com/arcio/rss/",
        ],
        description="RSS feed URLs for news headlines"
    )

    tts_voice: str = Field(default="alloy", description="OpenAI TTS voice")
    bed_volume_db: float = Field(default=-18.0, description="Background bed volume in dB")
    break_freshness_minutes: int = Field(default=50, description="Break freshness threshold")

    def validate_production_config(self) -> None:
        """Validate that required production fields are set.

        Raises:
            ValueError: If required fields are missing
        """
        errors = []
        if self.station_lat is None:
            errors.append("RADIO_STATION_LAT is required for weather data")
        if self.station_lon is None:
            errors.append("RADIO_STATION_LON is required for weather data")
        if self.llm_api_key is None:
            errors.append("RADIO_LLM_API_KEY is required for content generation")
        if self.tts_api_key is None:
            errors.append("RADIO_TTS_API_KEY is required for voice synthesis")

        if errors:
            raise ValueError(
                "Production configuration incomplete:\n  - " + "\n  - ".join(errors)
            )

    # Derived paths
    @property
    def assets_path(self) -> Path:
        return self.base_path / "assets"

    @property
    def music_path(self) -> Path:
        return self.assets_path / "music"

    @property
    def beds_path(self) -> Path:
        return self.assets_path / "beds"

    @property
    def breaks_path(self) -> Path:
        return self.assets_path / "breaks"

    @property
    def breaks_archive_path(self) -> Path:
        return self.breaks_path / "archive"

    @property
    def safety_path(self) -> Path:
        return self.assets_path / "safety"

    @property
    def drops_path(self) -> Path:
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        return self.base_path / "tmp"

    @property
    def state_path(self) -> Path:
        return self.base_path / "state"

    @property
    def db_path(self) -> Path:
        return self.base_path / "db" / "radio.sqlite3"

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs" / "jobs.jsonl"

    @property
    def liquidsoap_sock_path(self) -> Path:
        return Path("/run/liquidsoap/radio.sock")


# Global config instance
config = RadioConfig()
