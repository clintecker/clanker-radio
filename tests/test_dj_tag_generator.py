"""Tests for DJ tag generator."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from ai_radio.dj_tag_generator import DJTagGenerator, GenerationProgress


class TestDJTagGenerator:
    """Test DJ tag generation with Gemini TTS."""

    def test_initialization_requires_api_key(self):
        """Test that generator requires valid API key."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = None
            with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
                DJTagGenerator()

    def test_initialization_success(self):
        """Test successful generator initialization."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()
            assert generator.api_key == "test-key"

    def test_generate_validates_empty_text(self):
        """Test that empty text is rejected."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                output_path = Path(f.name)

            try:
                result = generator.generate(
                    text="",
                    output_path=output_path,
                    voice="Kore"
                )
                assert result is None
            finally:
                output_path.unlink(missing_ok=True)

    def test_generate_validates_text_length(self):
        """Test that text exceeding max length is rejected."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"
            generator = DJTagGenerator()

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                output_path = Path(f.name)

            try:
                # Generate text > 5000 characters
                long_text = "a" * 5001
                result = generator.generate(
                    text=long_text,
                    output_path=output_path,
                    voice="Kore"
                )
                assert result is None
            finally:
                output_path.unlink(missing_ok=True)

    @patch('ai_radio.dj_tag_generator.subprocess.run')
    def test_generate_calls_gemini_api(self, mock_subprocess):
        """Test that generate calls Gemini API with correct parameters."""
        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"

            # Mock successful ffmpeg conversion
            mock_subprocess.return_value = Mock(returncode=0, stderr="")

            with patch('ai_radio.dj_tag_generator.genai') as mock_genai:
                # Mock Gemini client and response
                mock_client = MagicMock()
                mock_genai.Client.return_value = mock_client

                mock_response = MagicMock()
                mock_part = MagicMock()
                mock_part.inline_data.data = b"fake_pcm_data"
                mock_response.candidates = [MagicMock()]
                mock_response.candidates[0].content.parts = [mock_part]

                mock_client.models.generate_content.return_value = mock_response

                generator = DJTagGenerator()

                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    output_path = Path(f.name)

                try:
                    result = generator.generate(
                        text="Test DJ tag",
                        output_path=output_path,
                        voice="Laomedeia",
                        temperature=2.0,
                        speaking_rate=1.0,
                        pitch=0.0,
                        style_prompt="excited and energetic"
                    )

                    assert result is not None
                    assert result.file_path == output_path
                    assert result.voice == "Laomedeia"

                    # Verify API was called
                    mock_client.models.generate_content.assert_called_once()
                finally:
                    output_path.unlink(missing_ok=True)

    def test_progress_callback_is_called(self):
        """Test that progress callback receives updates."""
        progress_updates = []

        def progress_callback(progress: GenerationProgress):
            progress_updates.append(progress)

        with patch('ai_radio.dj_tag_generator.config') as mock_config:
            mock_config.gemini_api_key = "test-key"

            with patch('ai_radio.dj_tag_generator.subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0, stderr="")

                with patch('ai_radio.dj_tag_generator.genai') as mock_genai:
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client

                    mock_response = MagicMock()
                    mock_part = MagicMock()
                    mock_part.inline_data.data = b"fake_pcm_data"
                    mock_response.candidates = [MagicMock()]
                    mock_response.candidates[0].content.parts = [mock_part]

                    mock_client.models.generate_content.return_value = mock_response

                    generator = DJTagGenerator()

                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        output_path = Path(f.name)

                    try:
                        generator.generate(
                            text="Test",
                            output_path=output_path,
                            voice="Kore",
                            progress_callback=progress_callback
                        )

                        # Should have received at least: started, generating, converting, complete
                        assert len(progress_updates) >= 4
                        assert any(p.message == "Starting generation..." for p in progress_updates)
                        assert any(p.message == "Generating audio..." for p in progress_updates)
                        assert any("Converting" in p.message for p in progress_updates)
                        assert any("Complete" in p.message for p in progress_updates)
                    finally:
                        output_path.unlink(missing_ok=True)
