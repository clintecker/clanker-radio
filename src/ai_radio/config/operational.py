"""Operational runtime behavior configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OperationalConfig(BaseSettings):
    """Operational runtime behavior settings.

    Environment variables:
        RADIO_BREAK_FRESHNESS_MINUTES: Break freshness threshold
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    break_freshness_minutes: int = Field(
        default=50,
        description="Break freshness threshold for content scheduling"
    )
