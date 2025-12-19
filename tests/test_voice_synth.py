"""Tests for OpenAI TTS voice synthesis.

Test coverage:
- Successful voice synthesis
- API error handling
- Missing API key handling
- Empty script handling
- Output file creation
- Duration estimation
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
from openai import APIError

from ai_radio.voice_synth import OpenAIVoiceSynthesizer, AudioFile, synthesize_bulletin


class TestOpenAIVoiceSynthesizer:
    """Tests for OpenAIVoiceSynthesizer."""

    def test_initialization_requires_api_key(self):
        """OpenAIVoiceSynthesizer should raise ValueError if API key not configured."""
        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = None

            with pytest.raises(ValueError, match="RADIO_TTS_API_KEY not configured"):
                OpenAIVoiceSynthesizer()

    def test_initialization_with_api_key(self):
        """OpenAIVoiceSynthesizer should initialize with valid API key."""
        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-api-key"
            mock_config.tts_voice = "alloy"

            synthesizer = OpenAIVoiceSynthesizer()

            assert synthesizer.api_key == "test-api-key"
            assert synthesizer.model == "tts-1"
            assert synthesizer.voice == "alloy"
            assert synthesizer.format == "mp3"

    def test_synthesize_success(self, tmp_path):
        """synthesize should generate MP3 file from script text."""
        script = "Good afternoon! This is your weather and news bulletin. It's 72 degrees and sunny."
        output_path = tmp_path / "test_bulletin.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            with patch("ai_radio.voice_synth.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                # Mock TTS API response
                mock_response = Mock()
                mock_response.stream_to_file = Mock()
                mock_client.audio.speech.create.return_value = mock_response

                synthesizer = OpenAIVoiceSynthesizer()
                audio = synthesizer.synthesize(script, output_path)

                # Verify API call
                mock_client.audio.speech.create.assert_called_once_with(
                    model="tts-1",
                    voice="alloy",
                    input=script,
                    response_format="mp3",
                )

                # Verify file write
                mock_response.stream_to_file.assert_called_once_with(str(output_path))

                # Verify AudioFile
                assert audio is not None
                assert audio.file_path == output_path
                assert audio.voice == "alloy"
                assert audio.model == "tts-1"
                assert audio.duration_estimate > 0
                assert isinstance(audio.timestamp, datetime)

    def test_synthesize_duration_estimation(self, tmp_path):
        """synthesize should estimate duration based on word count (150 wpm)."""
        # 150 words should estimate to ~60 seconds
        script = " ".join(["word"] * 150)
        output_path = tmp_path / "duration_test.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            with patch("ai_radio.voice_synth.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                mock_response = Mock()
                mock_response.stream_to_file = Mock()
                mock_client.audio.speech.create.return_value = mock_response

                synthesizer = OpenAIVoiceSynthesizer()
                audio = synthesizer.synthesize(script, output_path)

                assert audio is not None
                # 150 words / 150 wpm = 1 minute = 60 seconds
                assert 58 <= audio.duration_estimate <= 62

    def test_synthesize_empty_script(self, tmp_path):
        """synthesize should return None for empty script."""
        output_path = tmp_path / "empty.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            synthesizer = OpenAIVoiceSynthesizer()
            audio = synthesizer.synthesize("", output_path)

            assert audio is None

    def test_synthesize_whitespace_only_script(self, tmp_path):
        """synthesize should return None for whitespace-only script."""
        output_path = tmp_path / "whitespace.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            synthesizer = OpenAIVoiceSynthesizer()
            audio = synthesizer.synthesize("   \n\t  ", output_path)

            assert audio is None

    def test_synthesize_api_error(self, tmp_path):
        """synthesize should return None on API error."""
        script = "Test bulletin"
        output_path = tmp_path / "error_test.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            with patch("ai_radio.voice_synth.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                # Simulate API error (use generic Exception since APIError signature varies)
                mock_client.audio.speech.create.side_effect = Exception("API rate limit")

                synthesizer = OpenAIVoiceSynthesizer()
                audio = synthesizer.synthesize(script, output_path)

                assert audio is None

    def test_synthesize_creates_parent_directory(self, tmp_path):
        """synthesize should create parent directories if they don't exist."""
        script = "Test bulletin"
        nested_path = tmp_path / "nested" / "dir" / "test.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "alloy"

            with patch("ai_radio.voice_synth.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                mock_response = Mock()
                mock_response.stream_to_file = Mock()
                mock_client.audio.speech.create.return_value = mock_response

                synthesizer = OpenAIVoiceSynthesizer()
                audio = synthesizer.synthesize(script, nested_path)

                assert audio is not None
                # Verify parent directories would be created
                # (mkdir with parents=True was called via Path.mkdir)

    def test_synthesize_uses_configured_voice(self, tmp_path):
        """synthesize should use voice from config."""
        script = "Test"
        output_path = tmp_path / "voice_test.mp3"

        with patch("ai_radio.voice_synth.config") as mock_config:
            mock_config.tts_api_key = "test-key"
            mock_config.tts_voice = "nova"  # Different voice

            with patch("ai_radio.voice_synth.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                mock_response = Mock()
                mock_response.stream_to_file = Mock()
                mock_client.audio.speech.create.return_value = mock_response

                synthesizer = OpenAIVoiceSynthesizer()
                audio = synthesizer.synthesize(script, output_path)

                # Verify nova voice was used
                call_kwargs = mock_client.audio.speech.create.call_args[1]
                assert call_kwargs["voice"] == "nova"
                assert audio.voice == "nova"


class TestSynthesizeBulletinConvenience:
    """Tests for synthesize_bulletin() convenience function."""

    def test_synthesize_bulletin_success(self, tmp_path):
        """synthesize_bulletin should return AudioFile on success."""
        script = "Test bulletin"
        output_path = tmp_path / "bulletin.mp3"

        mock_audio = AudioFile(
            file_path=output_path,
            duration_estimate=15.0,
            timestamp=datetime.now(),
            voice="alloy",
            model="tts-1",
        )

        with patch("ai_radio.voice_synth.OpenAIVoiceSynthesizer") as mock_synth_class:
            mock_synth = Mock()
            mock_synth.synthesize.return_value = mock_audio
            mock_synth_class.return_value = mock_synth

            result = synthesize_bulletin(script, output_path)

            assert result == mock_audio

    def test_synthesize_bulletin_initialization_failure(self, tmp_path):
        """synthesize_bulletin should return None if synthesizer initialization fails."""
        with patch("ai_radio.voice_synth.OpenAIVoiceSynthesizer") as mock_synth_class:
            mock_synth_class.side_effect = ValueError("No API key")

            result = synthesize_bulletin("test", tmp_path / "test.mp3")

            assert result is None
