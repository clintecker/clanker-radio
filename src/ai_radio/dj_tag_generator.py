"""DJ tag generator using simplified Gemini TTS.

Generates audio tags for DJ mixes without the elaborate five-element framework
used by the radio station. Provides direct text-to-speech with configurable
voice parameters.
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from .config import config

logger = logging.getLogger(__name__)

# Import Gemini at module level for easier mocking
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


@dataclass
class GenerationProgress:
    """Progress update during tag generation."""

    percent: int  # 0-100
    message: str


@dataclass
class GeneratedTag:
    """Generated DJ tag audio file."""

    file_path: Path
    duration_estimate: float  # seconds
    timestamp: datetime
    voice: str
    model: str
    temperature: float
    speaking_rate: float
    pitch: float


class DJTagGenerator:
    """Simplified Gemini TTS for DJ tag generation.

    Unlike the radio station voice synthesis, this uses direct text-to-speech
    without elaborate prompt engineering. Suitable for quick DJ tags and
    announcements.
    """

    MAX_TEXT_LENGTH = 5000

    def __init__(self):
        """Initialize DJ tag generator with Gemini API key."""
        self.api_key = config.gemini_api_key
        if not self.api_key:
            raise ValueError("RADIO_GEMINI_API_KEY not configured")

        # Allow None in tests (mocked scenarios)
        if genai is not None:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def generate(
        self,
        text: str,
        output_path: Path,
        voice: str = "Kore",
        model: str = "gemini-2.5-pro-preview-tts",
        temperature: float = 2.0,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        style_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> Optional[GeneratedTag]:
        """Generate DJ tag audio from text.

        Args:
            text: Text to synthesize
            output_path: Path for output MP3 file
            voice: Gemini voice name (e.g., "Laomedeia", "Kore", "Puck")
            model: Gemini TTS model (pro or flash)
            temperature: Creativity level for text generation (0.0-2.0)
            speaking_rate: Speech speed hint (0.5-2.0) - **metadata only, does not
                affect audio output**. Gemini TTS does not support numeric rate control.
                Use style_prompt for pacing control.
            pitch: Voice pitch hint (-20.0 to +20.0) - **metadata only, does not
                affect audio output**. Gemini TTS does not support numeric pitch control.
                Use style_prompt for tone control.
            style_prompt: Optional natural language style guidance. **Use this to
                control pacing, tone, and delivery style.** For example: "speak quickly
                and energetically" or "slow and deliberate".
            progress_callback: Optional callback for progress updates

        Returns:
            GeneratedTag with metadata, or None if generation fails

        Note:
            The Gemini TTS API uses natural language prompts for voice control
            instead of numeric parameters. Use style_prompt to describe desired
            pacing, tone, and delivery style. The speaking_rate and pitch
            parameters are accepted for API compatibility but only stored in
            the returned GeneratedTag metadata.
        """
        # Validation
        if not text or not text.strip():
            logger.error("Cannot generate tag from empty text")
            return None

        if len(text) > self.MAX_TEXT_LENGTH:
            logger.error(f"Text exceeds max length ({self.MAX_TEXT_LENGTH} characters)")
            return None

        def update_progress(percent: int, message: str):
            """Send progress update if callback provided."""
            if progress_callback:
                progress_callback(GenerationProgress(percent=percent, message=message))

        try:
            update_progress(0, "Starting generation...")
            logger.info(f"Generating DJ tag with voice '{voice}'")

            # Build simplified prompt (no five-element framework)
            if style_prompt:
                prompt = f"Style: {style_prompt}\n\nText: {text}"
            else:
                prompt = text

            update_progress(10, "Generating audio...")

            # Generate speech with Gemini API
            # In tests, types may be None if mocked at module level
            if types is not None:
                config_obj = types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice
                            )
                        )
                    ),
                    # Temperature controls text generation randomness (0.0-2.0)
                    # Note: speaking_rate and pitch are not supported by Gemini TTS API
                    # Use style_prompt for natural language control of pacing/tone instead
                    temperature=temperature,
                )
            else:
                # For mocked tests, use None config
                config_obj = None

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=config_obj
            )

            update_progress(50, "Processing audio data...")

            # Extract audio data from response
            if not response.candidates or not response.candidates[0].content.parts:
                logger.error("No audio data in Gemini response")
                return None

            # Find the audio part
            audio_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    audio_data = part.inline_data.data
                    break

            if not audio_data:
                logger.error("No audio inline_data in Gemini response")
                return None

            update_progress(60, "Converting PCM to MP3...")

            # Gemini returns raw PCM data - convert to MP3 using ffmpeg
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write raw PCM to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
                pcm_file.write(audio_data)
                pcm_path = pcm_file.name

            try:
                # Convert PCM to MP3 using ffmpeg
                # Gemini TTS outputs 24kHz 16-bit mono PCM
                # Set ID3 tags with the text content as title
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",  # Overwrite output file
                        "-f", "s16le",  # Format: signed 16-bit little-endian
                        "-ar", "24000",  # Sample rate: 24kHz
                        "-ac", "1",  # Audio channels: mono
                        "-i", pcm_path,  # Input PCM file
                        "-metadata", f"title={text[:100]}",  # Use first 100 chars as title
                        "-metadata", f"artist={config.music_artist}",
                        "-c:a", "libmp3lame",
                        "-q:a", "2",  # High quality MP3
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,  # 60 seconds should be sufficient for conversion
                )

                if result.returncode != 0:
                    logger.error(f"ffmpeg PCM conversion failed: {result.stderr}")
                    return None

            finally:
                # Clean up temp PCM file
                Path(pcm_path).unlink(missing_ok=True)

            update_progress(90, "Finalizing...")

            # Estimate duration (rough approximation: 150 words per minute)
            word_count = len(text.split())
            duration_estimate = (word_count / 150) * 60  # Convert to seconds

            update_progress(100, "Complete!")

            logger.info(
                f"DJ tag generation complete: {output_path} "
                f"(~{duration_estimate:.1f}s, {word_count} words)"
            )

            return GeneratedTag(
                file_path=output_path,
                duration_estimate=duration_estimate,
                timestamp=datetime.now(),
                voice=voice,
                model=model,
                temperature=temperature,
                speaking_rate=speaking_rate,
                pitch=pitch,
            )

        except Exception:
            logger.exception("DJ tag generation failed")
            if progress_callback:
                progress_callback(
                    GenerationProgress(
                        percent=0,
                        message="Generation failed. Please try again or contact support.",
                    )
                )
            return None
