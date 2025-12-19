"""Text-to-speech voice synthesis using OpenAI TTS API.

Converts bulletin scripts into MP3 audio files for radio broadcast.
Uses OpenAI TTS-1 model with configured voice selection.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI, APIError

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class AudioFile:
    """Generated audio file with metadata."""

    file_path: Path
    duration_estimate: float  # Estimated seconds (approximate, based on word count)
    timestamp: datetime
    voice: str
    model: str


class OpenAIVoiceSynthesizer:
    """OpenAI TTS voice synthesizer.

    Generates MP3 audio from text scripts using OpenAI's TTS API.
    Optimized for radio broadcast quality.
    """

    def __init__(self):
        """Initialize OpenAI TTS client with API key from config."""
        self.api_key = config.tts_api_key
        if not self.api_key:
            raise ValueError("RADIO_TTS_API_KEY not configured")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "tts-1"  # Standard quality (faster, lower cost)
        self.voice = config.tts_voice
        self.format = "mp3"

    def synthesize(
        self,
        script_text: str,
        output_path: Path,
    ) -> Optional[AudioFile]:
        """Synthesize speech from script text to MP3 file.

        Args:
            script_text: The bulletin script to synthesize
            output_path: Path where MP3 file will be saved

        Returns:
            AudioFile with metadata, or None if synthesis fails
        """
        if not script_text or not script_text.strip():
            logger.error("Cannot synthesize empty script")
            return None

        try:
            logger.info(f"Synthesizing speech with voice '{self.voice}'")

            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=script_text,
                response_format=self.format,
            )

            # Write audio data to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(str(output_path))

            # Estimate duration (rough approximation: 150 words per minute)
            word_count = len(script_text.split())
            duration_estimate = (word_count / 150) * 60  # Convert to seconds

            logger.info(
                f"Voice synthesis complete: {output_path} "
                f"(~{duration_estimate:.1f}s, {word_count} words)"
            )

            return AudioFile(
                file_path=output_path,
                duration_estimate=duration_estimate,
                timestamp=datetime.now(),
                voice=self.voice,
                model=self.model,
            )

        except APIError as e:
            logger.error(f"OpenAI TTS API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Voice synthesis failed: {e}")
            return None


def synthesize_bulletin(
    script_text: str,
    output_path: Path,
) -> Optional[AudioFile]:
    """Convenience function to synthesize bulletin audio.

    Args:
        script_text: Script text to convert to speech
        output_path: Path for output MP3 file

    Returns:
        AudioFile or None if synthesis fails
    """
    try:
        synthesizer = OpenAIVoiceSynthesizer()
        return synthesizer.synthesize(script_text, output_path)
    except ValueError as e:
        logger.error(f"Voice synthesizer initialization failed: {e}")
        return None
