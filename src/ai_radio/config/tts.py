"""Text-to-speech (TTS) configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TTSConfig(BaseSettings):
    """Text-to-speech provider configuration.

    Note: API keys are in APIKeysConfig.

    Environment variables:
        RADIO_TTS_PROVIDER: TTS provider ('openai' or 'gemini')
        RADIO_GEMINI_TTS_MODEL: Gemini TTS model name
        RADIO_GEMINI_TTS_VOICE: Gemini TTS voice name
        RADIO_TTS_VOICE: OpenAI TTS voice name
        RADIO_TTS_REQUEST_TIMEOUT_SEC: Per-request TTS HTTP timeout in seconds
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # TTS Provider
    tts_provider: str = Field(
        default="gemini",
        description="TTS provider: 'openai' or 'gemini'"
    )

    # Gemini TTS Settings
    gemini_tts_model: str = Field(
        default="gemini-2.5-pro-preview-tts",
        description="Gemini TTS model (gemini-2.5-flash-preview-tts or gemini-2.5-pro-preview-tts)"
    )
    gemini_tts_voice: str = Field(
        default="Kore",
        description="Gemini TTS voice name"
    )

    # OpenAI TTS Settings
    tts_voice: str = Field(
        default="alloy",
        description="OpenAI TTS voice"
    )

    # Shared request limits
    tts_request_timeout_sec: float = Field(
        default=90.0,
        gt=0,
        description="Per-request HTTP timeout for TTS providers, in seconds. "
                    "Must be well under the systemd TimeoutSec of the break-gen unit (300s) "
                    "so a hung provider fails over instead of killing the whole run."
    )
