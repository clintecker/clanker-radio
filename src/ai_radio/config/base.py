"""Configuration composition root."""
import logging
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
            import defusedxml.ElementTree as ET
            icecast_config = Path("/etc/icecast2/icecast.xml")
            if icecast_config.exists():
                tree = ET.parse(icecast_config)
                root = tree.getroot()
                admin_pass_elem = root.find('.//authentication/admin-password')
                if admin_pass_elem is not None and admin_pass_elem.text:
                    return admin_pass_elem.text
        except Exception as e:
            logging.warning(f"Failed to read Icecast admin password from XML: {e}")

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
        # Return plain string for backward compatibility (not SecretStr)
        return self.api_keys.llm_api_key.get_secret_value() if self.api_keys.llm_api_key else None

    @property
    def tts_api_key(self):
        """DEPRECATED: Use config.api_keys.tts_api_key instead."""
        warnings.warn(
            "'config.tts_api_key' is deprecated. Use 'config.api_keys.tts_api_key' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Return plain string for backward compatibility (not SecretStr)
        return self.api_keys.tts_api_key.get_secret_value() if self.api_keys.tts_api_key else None

    @property
    def gemini_api_key(self):
        """DEPRECATED: Use config.api_keys.gemini_api_key instead."""
        warnings.warn(
            "'config.gemini_api_key' is deprecated. Use 'config.api_keys.gemini_api_key' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Return plain string for backward compatibility (not SecretStr)
        return self.api_keys.gemini_api_key.get_secret_value() if self.api_keys.gemini_api_key else None

    @property
    def announcer_name(self) -> str:
        """DEPRECATED: Use config.announcer.announcer_name instead."""
        warnings.warn(
            "'config.announcer_name' is deprecated. Use 'config.announcer.announcer_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.announcer_name

    @property
    def energy_level(self) -> int:
        """DEPRECATED: Use config.announcer.energy_level instead."""
        warnings.warn(
            "'config.energy_level' is deprecated. Use 'config.announcer.energy_level' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.energy_level

    @property
    def vibe_keywords(self) -> str:
        """DEPRECATED: Use config.announcer.vibe_keywords instead."""
        warnings.warn(
            "'config.vibe_keywords' is deprecated. Use 'config.announcer.vibe_keywords' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.vibe_keywords

    @property
    def max_riffs_per_break(self) -> int:
        """DEPRECATED: Use config.announcer.max_riffs_per_break instead."""
        warnings.warn(
            "'config.max_riffs_per_break' is deprecated. Use 'config.announcer.max_riffs_per_break' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.max_riffs_per_break

    @property
    def max_exclamations_per_break(self) -> int:
        """DEPRECATED: Use config.announcer.max_exclamations_per_break instead."""
        warnings.warn(
            "'config.max_exclamations_per_break' is deprecated. Use 'config.announcer.max_exclamations_per_break' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.max_exclamations_per_break

    @property
    def unhinged_percentage(self) -> int:
        """DEPRECATED: Use config.announcer.unhinged_percentage instead."""
        warnings.warn(
            "'config.unhinged_percentage' is deprecated. Use 'config.announcer.unhinged_percentage' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.unhinged_percentage

    @property
    def unhinged_triggers(self) -> str:
        """DEPRECATED: Use config.announcer.unhinged_triggers instead."""
        warnings.warn(
            "'config.unhinged_triggers' is deprecated. Use 'config.announcer.unhinged_triggers' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.unhinged_triggers

    @property
    def humor_priority(self) -> str:
        """DEPRECATED: Use config.announcer.humor_priority instead."""
        warnings.warn(
            "'config.humor_priority' is deprecated. Use 'config.announcer.humor_priority' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.humor_priority

    @property
    def allowed_comedy(self) -> str:
        """DEPRECATED: Use config.announcer.allowed_comedy instead."""
        warnings.warn(
            "'config.allowed_comedy' is deprecated. Use 'config.announcer.allowed_comedy' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.allowed_comedy

    @property
    def banned_comedy(self) -> str:
        """DEPRECATED: Use config.announcer.banned_comedy instead."""
        warnings.warn(
            "'config.banned_comedy' is deprecated. Use 'config.announcer.banned_comedy' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.banned_comedy

    @property
    def sentence_length_target(self) -> str:
        """DEPRECATED: Use config.announcer.sentence_length_target instead."""
        warnings.warn(
            "'config.sentence_length_target' is deprecated. Use 'config.announcer.sentence_length_target' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.sentence_length_target

    @property
    def max_adjectives_per_sentence(self) -> int:
        """DEPRECATED: Use config.announcer.max_adjectives_per_sentence instead."""
        warnings.warn(
            "'config.max_adjectives_per_sentence' is deprecated. Use 'config.announcer.max_adjectives_per_sentence' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.max_adjectives_per_sentence

    @property
    def natural_disfluency(self) -> str:
        """DEPRECATED: Use config.announcer.natural_disfluency instead."""
        warnings.warn(
            "'config.natural_disfluency' is deprecated. Use 'config.announcer.natural_disfluency' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.natural_disfluency

    @property
    def banned_ai_phrases(self) -> str:
        """DEPRECATED: Use config.announcer.banned_ai_phrases instead."""
        warnings.warn(
            "'config.banned_ai_phrases' is deprecated. Use 'config.announcer.banned_ai_phrases' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.banned_ai_phrases

    @property
    def radio_resets(self) -> str:
        """DEPRECATED: Use config.announcer.radio_resets instead."""
        warnings.warn(
            "'config.radio_resets' is deprecated. Use 'config.announcer.radio_resets' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.radio_resets

    @property
    def listener_relationship(self) -> str:
        """DEPRECATED: Use config.announcer.listener_relationship instead."""
        warnings.warn(
            "'config.listener_relationship' is deprecated. Use 'config.announcer.listener_relationship' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.listener_relationship

    @property
    def music_artist(self) -> str:
        """DEPRECATED: Use config.audio.music_artist instead."""
        warnings.warn(
            "'config.music_artist' is deprecated. Use 'config.audio.music_artist' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.music_artist

    @property
    def station_location(self) -> str:
        """DEPRECATED: Use config.station.station_location instead."""
        warnings.warn(
            "'config.station_location' is deprecated. Use 'config.station.station_location' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.station.station_location

    @property
    def station_tz(self) -> str:
        """DEPRECATED: Use config.station.station_tz instead."""
        warnings.warn(
            "'config.station_tz' is deprecated. Use 'config.station.station_tz' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.station.station_tz

    @property
    def world_setting(self) -> str:
        """DEPRECATED: Use config.world.world_setting instead."""
        warnings.warn(
            "'config.world_setting' is deprecated. Use 'config.world.world_setting' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.world.world_setting

    @property
    def world_tone(self) -> str:
        """DEPRECATED: Use config.world.world_tone instead."""
        warnings.warn(
            "'config.world_tone' is deprecated. Use 'config.world.world_tone' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.world.world_tone

    # Path properties (delegate to paths domain @property methods)
    @property
    def liquidsoap_sock_path(self) -> Path:
        """DEPRECATED: Use config.paths.liquidsoap_sock_path instead."""
        warnings.warn(
            "'config.liquidsoap_sock_path' is deprecated. Use 'config.paths.liquidsoap_sock_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.liquidsoap_sock_path

    @property
    def music_path(self) -> Path:
        """DEPRECATED: Use config.paths.music_path instead."""
        warnings.warn(
            "'config.music_path' is deprecated. Use 'config.paths.music_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.music_path

    @property
    def db_path(self) -> Path:
        """DEPRECATED: Use config.paths.db_path instead."""
        warnings.warn(
            "'config.db_path' is deprecated. Use 'config.paths.db_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.db_path

    @property
    def public_path(self) -> Path:
        """DEPRECATED: Use config.paths.public_path instead."""
        warnings.warn(
            "'config.public_path' is deprecated. Use 'config.paths.public_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.public_path

    # Audio mixing configuration shims
    @property
    def bed_volume_db(self) -> float:
        """DEPRECATED: Use config.audio.bed_volume_db instead."""
        warnings.warn(
            "'config.bed_volume_db' is deprecated. Use 'config.audio.bed_volume_db' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.bed_volume_db

    @property
    def bed_preroll_seconds(self) -> float:
        """DEPRECATED: Use config.audio.bed_preroll_seconds instead."""
        warnings.warn(
            "'config.bed_preroll_seconds' is deprecated. Use 'config.audio.bed_preroll_seconds' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.bed_preroll_seconds

    @property
    def bed_fadein_seconds(self) -> float:
        """DEPRECATED: Use config.audio.bed_fadein_seconds instead."""
        warnings.warn(
            "'config.bed_fadein_seconds' is deprecated. Use 'config.audio.bed_fadein_seconds' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.bed_fadein_seconds

    @property
    def bed_postroll_seconds(self) -> float:
        """DEPRECATED: Use config.audio.bed_postroll_seconds instead."""
        warnings.warn(
            "'config.bed_postroll_seconds' is deprecated. Use 'config.audio.bed_postroll_seconds' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.bed_postroll_seconds

    @property
    def bed_fadeout_seconds(self) -> float:
        """DEPRECATED: Use config.audio.bed_fadeout_seconds instead."""
        warnings.warn(
            "'config.bed_fadeout_seconds' is deprecated. Use 'config.audio.bed_fadeout_seconds' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.audio.bed_fadeout_seconds

    # Path configuration shims
    @property
    def breaks_path(self) -> Path:
        """DEPRECATED: Use config.paths.breaks_path instead."""
        warnings.warn(
            "'config.breaks_path' is deprecated. Use 'config.paths.breaks_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.breaks_path

    @property
    def beds_path(self) -> Path:
        """DEPRECATED: Use config.paths.beds_path instead."""
        warnings.warn(
            "'config.beds_path' is deprecated. Use 'config.paths.beds_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.beds_path

    @property
    def bumpers_path(self) -> Path:
        """DEPRECATED: Use config.paths.bumpers_path instead."""
        warnings.warn(
            "'config.bumpers_path' is deprecated. Use 'config.paths.bumpers_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.bumpers_path

    @property
    def safety_path(self) -> Path:
        """DEPRECATED: Use config.paths.safety_path instead."""
        warnings.warn(
            "'config.safety_path' is deprecated. Use 'config.paths.safety_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.safety_path

    @property
    def drops_path(self) -> Path:
        """DEPRECATED: Use config.paths.drops_path instead."""
        warnings.warn(
            "'config.drops_path' is deprecated. Use 'config.paths.drops_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.drops_path

    @property
    def tmp_path(self) -> Path:
        """DEPRECATED: Use config.paths.tmp_path instead."""
        warnings.warn(
            "'config.tmp_path' is deprecated. Use 'config.paths.tmp_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.tmp_path

    @property
    def breaks_archive_path(self) -> Path:
        """DEPRECATED: Use config.paths.breaks_archive_path instead."""
        warnings.warn(
            "'config.breaks_archive_path' is deprecated. Use 'config.paths.breaks_archive_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.breaks_archive_path

    @property
    def state_path(self) -> Path:
        """DEPRECATED: Use config.paths.state_path instead."""
        warnings.warn(
            "'config.state_path' is deprecated. Use 'config.paths.state_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.state_path

    @property
    def recent_weather_phrases_path(self) -> Path:
        """DEPRECATED: Use config.paths.recent_weather_phrases_path instead."""
        warnings.warn(
            "'config.recent_weather_phrases_path' is deprecated. Use 'config.paths.recent_weather_phrases_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.recent_weather_phrases_path

    # Content sources configuration shims
    @property
    def news_rss_feeds(self) -> dict[str, list[str]]:
        """DEPRECATED: Use config.content.news_rss_feeds instead."""
        warnings.warn(
            "'config.news_rss_feeds' is deprecated. Use 'config.content.news_rss_feeds' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.content.news_rss_feeds

    @property
    def nws_office(self):
        """DEPRECATED: Use config.content.nws_office instead."""
        warnings.warn(
            "'config.nws_office' is deprecated. Use 'config.content.nws_office' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.content.nws_office

    @property
    def nws_grid_x(self):
        """DEPRECATED: Use config.content.nws_grid_x instead."""
        warnings.warn(
            "'config.nws_grid_x' is deprecated. Use 'config.content.nws_grid_x' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.content.nws_grid_x

    @property
    def nws_grid_y(self):
        """DEPRECATED: Use config.content.nws_grid_y instead."""
        warnings.warn(
            "'config.nws_grid_y' is deprecated. Use 'config.content.nws_grid_y' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.content.nws_grid_y

    @property
    def hallucinate_news(self) -> bool:
        """DEPRECATED: Use config.content.hallucinate_news instead."""
        warnings.warn(
            "'config.hallucinate_news' is deprecated. Use 'config.content.hallucinate_news' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.content.hallucinate_news

    # TTS configuration shims
    @property
    def tts_provider(self) -> str:
        """DEPRECATED: Use config.tts.tts_provider instead."""
        warnings.warn(
            "'config.tts_provider' is deprecated. Use 'config.tts.tts_provider' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.tts.tts_provider

    @property
    def tts_voice(self) -> str:
        """DEPRECATED: Use config.tts.tts_voice instead."""
        warnings.warn(
            "'config.tts_voice' is deprecated. Use 'config.tts.tts_voice' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.tts.tts_voice

    @property
    def gemini_tts_model(self) -> str:
        """DEPRECATED: Use config.tts.gemini_tts_model instead."""
        warnings.warn(
            "'config.gemini_tts_model' is deprecated. Use 'config.tts.gemini_tts_model' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.tts.gemini_tts_model

    @property
    def gemini_tts_voice(self) -> str:
        """DEPRECATED: Use config.tts.gemini_tts_voice instead."""
        warnings.warn(
            "'config.gemini_tts_voice' is deprecated. Use 'config.tts.gemini_tts_voice' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.tts.gemini_tts_voice

    # TODO: Add shims for all commonly accessed fields
    # Run `grep -r "config\." src/ scripts/` to find usages
