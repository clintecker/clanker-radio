"""Tests for APIKeysConfig domain configuration."""


import pytest
from pydantic import SecretStr

from ai_radio.config.api_keys import APIKeysConfig


class TestAPIKeysConfig:
    """Tests for APIKeysConfig."""

    def test_default_llm_api_key_none(self):
        """llm_api_key should default to None."""
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.llm_api_key is None

    def test_llm_api_key_from_env(self, monkeypatch):
        """llm_api_key should load from RADIO_LLM_API_KEY env var."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-llm-key-123")
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.llm_api_key is not None
        assert api_keys.llm_api_key.get_secret_value() == "test-llm-key-123"

    def test_llm_api_key_is_secret_str(self, monkeypatch):
        """llm_api_key should be SecretStr type."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-key")
        api_keys = APIKeysConfig(_env_file=None)
        assert isinstance(api_keys.llm_api_key, SecretStr)

    def test_llm_api_key_not_in_repr(self, monkeypatch):
        """llm_api_key should not appear in repr (SecretStr protection)."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "secret-key-123")
        api_keys = APIKeysConfig(_env_file=None)
        repr_str = repr(api_keys)
        assert "secret-key-123" not in repr_str
        assert "**********" in repr_str or "SecretStr" in repr_str

    def test_default_tts_api_key_none(self):
        """tts_api_key should default to None."""
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.tts_api_key is None

    def test_tts_api_key_from_env(self, monkeypatch):
        """tts_api_key should load from RADIO_TTS_API_KEY env var."""
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-tts-key-456")
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.tts_api_key is not None
        assert api_keys.tts_api_key.get_secret_value() == "test-tts-key-456"

    def test_tts_api_key_is_secret_str(self, monkeypatch):
        """tts_api_key should be SecretStr type."""
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-key")
        api_keys = APIKeysConfig(_env_file=None)
        assert isinstance(api_keys.tts_api_key, SecretStr)

    def test_default_gemini_api_key_none(self):
        """gemini_api_key should default to None."""
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.gemini_api_key is None

    def test_gemini_api_key_from_env(self, monkeypatch):
        """gemini_api_key should load from RADIO_GEMINI_API_KEY env var."""
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "test-gemini-key-789")
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.gemini_api_key is not None
        assert api_keys.gemini_api_key.get_secret_value() == "test-gemini-key-789"

    def test_gemini_api_key_is_secret_str(self, monkeypatch):
        """gemini_api_key should be SecretStr type."""
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "test-key")
        api_keys = APIKeysConfig(_env_file=None)
        assert isinstance(api_keys.gemini_api_key, SecretStr)

    def test_all_keys_none_by_default(self):
        """All API keys should be None by default (optional for testing)."""
        api_keys = APIKeysConfig(_env_file=None)
        assert api_keys.llm_api_key is None
        assert api_keys.tts_api_key is None
        assert api_keys.gemini_api_key is None

    def test_multiple_keys_from_env(self, monkeypatch):
        """Multiple API keys can be loaded from env vars simultaneously."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "llm-key")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "tts-key")
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "gemini-key")

        api_keys = APIKeysConfig(_env_file=None)

        assert api_keys.llm_api_key.get_secret_value() == "llm-key"
        assert api_keys.tts_api_key.get_secret_value() == "tts-key"
        assert api_keys.gemini_api_key.get_secret_value() == "gemini-key"

    def test_validate_production_fails_without_llm_key(self, monkeypatch):
        """validate_production should raise ValueError if llm_api_key is None."""
        monkeypatch.setenv("RADIO_TTS_API_KEY", "tts-key")
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "gemini-key")
        api_keys = APIKeysConfig(_env_file=None)

        with pytest.raises(ValueError, match="RADIO_LLM_API_KEY is required"):
            api_keys.validate_production()

    def test_validate_production_fails_without_tts_key(self, monkeypatch):
        """validate_production should raise ValueError if tts_api_key is None."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "llm-key")
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "gemini-key")
        api_keys = APIKeysConfig(_env_file=None)

        with pytest.raises(ValueError, match="RADIO_TTS_API_KEY is required"):
            api_keys.validate_production()

    def test_validate_production_succeeds_with_all_keys(self, monkeypatch):
        """validate_production should succeed when all keys are present."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "llm-key")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "tts-key")
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "gemini-key")
        api_keys = APIKeysConfig(_env_file=None)

        # Should not raise
        api_keys.validate_production()

    def test_validate_production_fails_with_empty_llm_key(self, monkeypatch):
        """validate_production should reject empty string API keys."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "valid-key")
        api_keys = APIKeysConfig(_env_file=None)

        with pytest.raises(ValueError, match="RADIO_LLM_API_KEY is required"):
            api_keys.validate_production()

    def test_validate_production_fails_with_empty_tts_key(self, monkeypatch):
        """validate_production should reject empty string API keys."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "valid-key")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "")
        api_keys = APIKeysConfig(_env_file=None)

        with pytest.raises(ValueError, match="RADIO_TTS_API_KEY is required"):
            api_keys.validate_production()

    def test_validate_production_fails_with_whitespace_only_keys(self, monkeypatch):
        """validate_production should reject whitespace-only API keys."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "   ")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "valid-key")
        api_keys = APIKeysConfig(_env_file=None)

        with pytest.raises(ValueError, match="RADIO_LLM_API_KEY is required"):
            api_keys.validate_production()
