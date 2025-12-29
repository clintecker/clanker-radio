"""Station identity and location configuration."""

from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StationIdentityConfig(BaseSettings):
    """Station identity and location metadata.

    Environment variables:
        RADIO_STATION_NAME: Station name for on-air identification
        RADIO_STATION_LOCATION: Station location for brand identity
        RADIO_STATION_TZ: IANA timezone (e.g., Pacific/Honolulu)
        RADIO_STATION_LAT: Station latitude for weather data
        RADIO_STATION_LON: Station longitude for weather data
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Station identity
    station_name: str = Field(default="WKRP Coconut Island", description="Station name for on-air identification")
    station_location: str = Field(default="Coconut Island", description="Station location for brand identity")
    station_tz: str = Field(default="Pacific/Honolulu", description="IANA timezone")

    # Geographic coordinates (optional, for weather data)
    station_lat: Optional[float] = Field(default=None, description="Station latitude for weather data")
    station_lon: Optional[float] = Field(default=None, description="Station longitude for weather data")

    @field_validator("station_lat")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        """Validate latitude is within valid range."""
        if v is not None and (v < -90 or v > 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("station_lon")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        """Validate longitude is within valid range."""
        if v is not None and (v < -180 or v > 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v
