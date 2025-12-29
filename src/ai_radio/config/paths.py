"""Filesystem paths configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PathsConfig(BaseSettings):
    """Filesystem paths for AI Radio Station.

    All paths can be overridden via environment variables with RADIO_ prefix.

    Environment variables:
        RADIO_BASE_PATH: Base directory (default: /srv/ai_radio)
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Base path
    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Derived paths as properties
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
    def bumpers_path(self) -> Path:
        return self.assets_path / "bumpers"

    @property
    def safety_path(self) -> Path:
        return self.assets_path / "safety"

    @property
    def startup_path(self) -> Path:
        return self.assets_path / "startup.mp3"

    @property
    def drops_path(self) -> Path:
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        return self.base_path / "tmp"

    @property
    def public_path(self) -> Path:
        return self.base_path / "public"

    @property
    def state_path(self) -> Path:
        return self.base_path / "state"

    @property
    def recent_weather_phrases_path(self) -> Path:
        return self.state_path / "recent_weather_phrases.json"

    @property
    def db_path(self) -> Path:
        return self.base_path / "db" / "radio.sqlite3"

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs" / "jobs.jsonl"

    @property
    def liquidsoap_sock_path(self) -> Path:
        return Path("/run/liquidsoap/radio.sock")
