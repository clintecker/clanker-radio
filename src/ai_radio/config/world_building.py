"""World-building and setting configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorldBuildingConfig(BaseSettings):
    """World-building and setting configuration.

    Defines the SETTING - the world/universe in which the station exists.

    Environment variables:
        RADIO_WORLD_SETTING: The world/universe setting
        RADIO_WORLD_TONE: Emotional tone and vibe
        RADIO_WORLD_FRAMING: How to frame content through station personality
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    world_setting: str = Field(
        default="laid-back tropical island paradise",
        description="The world/universe setting for the station"
    )
    world_tone: str = Field(
        default="relaxed, friendly, warm, good vibes only, island time",
        description="Emotional tone and vibe of your station"
    )
    world_framing: str = Field(
        default="Broadcasting from our little slice of paradise. The news and weather filtered through the lens of island living - warm sun, cool breezes, and the sound of waves. We keep it real but keep it chill.",
        description="How to frame all content through your station's personality"
    )
