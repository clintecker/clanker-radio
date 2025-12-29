"""Tests for TTS (text-to-speech) configuration."""

from ai_radio.config.tts import TTSConfig


class TestTTSConfigDefaults:
    """Test default values for TTS configuration."""

    def test_tts_provider_default(self):
        """Test tts_provider has correct default value."""
        config = TTSConfig()
        assert config.tts_provider == "gemini"

    def test_gemini_tts_model_default(self):
        """Test gemini_tts_model has correct default value."""
        config = TTSConfig()
        assert config.gemini_tts_model == "gemini-2.5-pro-preview-tts"

    def test_gemini_tts_voice_default(self):
        """Test gemini_tts_voice has correct default value."""
        config = TTSConfig()
        assert config.gemini_tts_voice == "Kore"

    def test_tts_voice_default(self):
        """Test tts_voice has correct default value."""
        config = TTSConfig()
        assert config.tts_voice == "alloy"


class TestTTSConfigEnvironment:
    """Test environment variable overrides for TTS configuration."""

    def test_tts_provider_from_env(self, monkeypatch):
        """Test tts_provider can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_TTS_PROVIDER", "openai")
        config = TTSConfig()
        assert config.tts_provider == "openai"

    def test_gemini_tts_model_from_env(self, monkeypatch):
        """Test gemini_tts_model can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
        config = TTSConfig()
        assert config.gemini_tts_model == "gemini-2.5-flash-preview-tts"

    def test_gemini_tts_voice_from_env(self, monkeypatch):
        """Test gemini_tts_voice can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_GEMINI_TTS_VOICE", "Aoede")
        config = TTSConfig()
        assert config.gemini_tts_voice == "Aoede"

    def test_tts_voice_from_env(self, monkeypatch):
        """Test tts_voice can be overridden via environment variable."""
        monkeypatch.setenv("RADIO_TTS_VOICE", "nova")
        config = TTSConfig()
        assert config.tts_voice == "nova"
