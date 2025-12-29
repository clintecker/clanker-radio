"""Audio mixing and production configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioMixingConfig(BaseSettings):
    """Audio mixing and production settings.

    Environment variables:
        RADIO_BED_VOLUME_DB: Background bed volume in dB
        RADIO_BED_PREROLL_SECONDS: Bed starts before voice (ride in)
        RADIO_BED_FADEIN_SECONDS: Bed fade-in duration
        RADIO_BED_POSTROLL_SECONDS: Bed continues after voice (ride out)
        RADIO_BED_FADEOUT_SECONDS: Bed fade-out duration
        RADIO_MUSIC_ARTIST: Artist name for ingested music
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Audio bed volume and timing
    bed_volume_db: float = Field(default=-18.0, description="Background bed volume in dB")
    bed_preroll_seconds: float = Field(default=3.0, description="Bed starts before voice (ride in)")
    bed_fadein_seconds: float = Field(default=2.0, description="Bed fade-in duration at start")
    bed_postroll_seconds: float = Field(default=5.4, description="Bed continues after voice ends (ride out)")
    bed_fadeout_seconds: float = Field(default=3.0, description="Bed fade-out duration at end")

    # Music asset configuration
    music_artist: str = Field(
        default="Clint Ecker",
        description="Artist name for all ingested music (ID3 tags and database)"
    )
