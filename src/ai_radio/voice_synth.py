"""Text-to-speech voice synthesis using OpenAI or Gemini TTS API.

Converts bulletin scripts into MP3 audio files for radio broadcast.
Supports multiple TTS providers for voice comparison and selection.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

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


class GeminiVoiceSynthesizer:
    """Google Gemini TTS voice synthesizer.

    Generates MP3 audio from text scripts using Google's Gemini TTS API.
    Supports both Flash (low latency) and Pro (high quality) models.
    """

    def __init__(self):
        """Initialize Gemini TTS client with API key from config."""
        self.api_key = config.gemini_api_key
        if not self.api_key:
            raise ValueError("RADIO_GEMINI_API_KEY not configured")

        # Import google.genai (newer package)
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
        except ImportError:
            raise ValueError("google-genai package not installed. Run: pip install google-genai")

        self.client = self.genai.Client(api_key=self.api_key)
        self.model_name = config.gemini_tts_model
        self.voice = config.gemini_tts_voice

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
            logger.info(f"Synthesizing speech with Gemini voice '{self.voice}'")

            # Build Director's Notes prompt for dystopian DJ performance
            director_prompt = f"""# AUDIO PROFILE: {config.announcer_name}
## "The Dystopian DJ"

## THE SCENE: Late-Night Chicago Studio
A cramped studio in what used to be an office building. Flickering LED strips cast harsh shadows. The red "ON AIR" light is duct-taped to the wall. Outside, the neon glow of corporate towers cuts through the smog. Inside, it's just you, a mic, and the static hum of failing infrastructure. Broadcasting to whoever's still listening.

### DIRECTOR'S NOTES

Style:
* Tired but defiant. You've been doing this shift for years. The world fell apart, and you kept showing up.
* Dry humor. Wry observations. Occasionally frustrated by the absurdity of it all.
* NOT melodramatic. NOT performing dystopia. Just... living in it. Normalizing the chaos.
* Conversational warmth underneath the weariness. You're talking to fellow survivors, not a crowd.

Pacing:
* Medium-fast with purposeful pauses for emphasis
* Crisp consonants, clear enunciation
* Occasional micro-pauses before punchlines or important info
* Speed up slightly when excited about something, slow down when delivering bad news

Accent:
* Internet-native, coastal US or Canadian
* Mid-20s to mid-30s streamer/podcaster sound
* Subtle tech slang fluency without forcing it
* NOT cartoonish, NOT over-the-top

Breathing:
* Natural breath sounds between thoughts
* Slight vocal fry on tired moments (not constant)
* Exhale-sighs when delivering particularly bleak news

### TRANSCRIPT
{script_text}"""

            # Generate speech with new API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=director_prompt,
                config=self.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=self.types.SpeechConfig(
                        voice_config=self.types.VoiceConfig(
                            prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    )
                )
            )

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

            # Gemini returns raw PCM data - convert to MP3 using ffmpeg
            import subprocess
            import tempfile

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write raw PCM to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
                pcm_file.write(audio_data)
                pcm_path = pcm_file.name

            try:
                # Convert PCM to MP3 using ffmpeg
                # Gemini TTS outputs 24kHz 16-bit mono PCM
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",  # Overwrite output file
                        "-f", "s16le",  # Format: signed 16-bit little-endian
                        "-ar", "24000",  # Sample rate: 24kHz
                        "-ac", "1",  # Audio channels: mono
                        "-i", pcm_path,  # Input PCM file
                        "-c:a", "libmp3lame",
                        "-q:a", "2",  # High quality MP3
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0:
                    logger.error(f"ffmpeg PCM conversion failed: {result.stderr}")
                    return None

            finally:
                # Clean up temp PCM file
                Path(pcm_path).unlink(missing_ok=True)

            # Estimate duration (rough approximation: 150 words per minute)
            word_count = len(script_text.split())
            duration_estimate = (word_count / 150) * 60  # Convert to seconds

            logger.info(
                f"Gemini voice synthesis complete: {output_path} "
                f"(~{duration_estimate:.1f}s, {word_count} words)"
            )

            return AudioFile(
                file_path=output_path,
                duration_estimate=duration_estimate,
                timestamp=datetime.now(),
                voice=self.voice,
                model=self.model_name,
            )

        except Exception as e:
            logger.error(f"Gemini TTS error: {e}")
            return None


def synthesize_bulletin(
    script_text: str,
    output_path: Path,
) -> Optional[AudioFile]:
    """Convenience function to synthesize bulletin audio.

    Automatically selects TTS provider based on configuration.
    Falls back through multiple providers on quota/rate limit errors:
    1. Primary Gemini model (Pro or Flash, based on config)
    2. Alternative Gemini model (Flash if Pro failed, Pro if Flash failed)
    3. OpenAI TTS (final fallback)

    Args:
        script_text: Script text to convert to speech
        output_path: Path for output MP3 file

    Returns:
        AudioFile or None if synthesis fails
    """
    def is_quota_error(error: Exception) -> bool:
        """Check if error is quota/rate limit related."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            "quota", "rate limit", "429", "resource_exhausted"
        ])

    def try_gemini_model(model_name: str, voice: str) -> Optional[AudioFile]:
        """Try synthesizing with specific Gemini model."""
        try:
            logger.info(f"Attempting Gemini TTS: {model_name} with voice {voice}")

            # Temporarily override config for this attempt
            original_model = config.gemini_tts_model
            original_voice = config.gemini_tts_voice
            config.gemini_tts_model = model_name
            config.gemini_tts_voice = voice

            try:
                synthesizer = GeminiVoiceSynthesizer()
                result = synthesizer.synthesize(script_text, output_path)
                if result:
                    logger.info(f"✓ Gemini {model_name} succeeded")
                    return result
            finally:
                # Restore original config
                config.gemini_tts_model = original_model
                config.gemini_tts_voice = original_voice

        except Exception as e:
            if is_quota_error(e):
                logger.warning(f"✗ Gemini {model_name} quota exhausted")
            else:
                logger.error(f"✗ Gemini {model_name} failed: {e}")
        return None

    # Define fallback chain
    if config.tts_provider == "gemini":
        # Gemini is primary - try Pro then Flash then OpenAI
        attempts = [
            ("gemini-pro", "gemini-2.5-pro-preview-tts", "Kore"),
            ("gemini-flash", "gemini-2.5-flash-preview-tts", "Kore"),
            ("openai", None, None)
        ]
    else:
        # OpenAI is primary - try it then Gemini Pro then Flash
        attempts = [
            ("openai", None, None),
            ("gemini-pro", "gemini-2.5-pro-preview-tts", "Kore"),
            ("gemini-flash", "gemini-2.5-flash-preview-tts", "Kore")
        ]

    # Try each provider in fallback chain
    for provider_name, model_name, voice in attempts:
        try:
            if provider_name == "openai":
                logger.info(f"Attempting OpenAI TTS")
                synthesizer = OpenAIVoiceSynthesizer()
                result = synthesizer.synthesize(script_text, output_path)
                if result:
                    logger.info(f"✓ OpenAI TTS succeeded")
                    return result
            else:
                result = try_gemini_model(model_name, voice)
                if result:
                    return result

        except ValueError as e:
            logger.error(f"Failed to initialize {provider_name}: {e}")
            continue
        except Exception as e:
            if is_quota_error(e):
                logger.warning(f"✗ {provider_name} quota exhausted")
                continue
            else:
                logger.error(f"✗ {provider_name} failed: {e}")
                # Don't try other providers for non-quota errors
                if provider_name == config.tts_provider:
                    return None

    logger.error("All TTS providers failed")
    return None
