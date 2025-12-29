"""API keys and secrets configuration."""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIKeysConfig(BaseSettings):
    """API keys and secrets for AI Radio Station.

    All keys are optional (None by default) and use SecretStr to prevent
    accidental exposure in logs or error messages.

    Environment variables:
        RADIO_LLM_API_KEY: LLM provider API key (Claude)
        RADIO_TTS_API_KEY: TTS provider API key (OpenAI)
        RADIO_GEMINI_API_KEY: Google Gemini API key
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API keys - all optional, protected with SecretStr
    llm_api_key: Optional[SecretStr] = Field(default=None, description="LLM provider API key")
    tts_api_key: Optional[SecretStr] = Field(default=None, description="OpenAI TTS API key")
    gemini_api_key: Optional[SecretStr] = Field(default=None, description="Google Gemini API key")
