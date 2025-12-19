"""Break generation orchestration.

Coordinates the full content generation pipeline:
1. Fetch weather and news data
2. Generate bulletin script with Claude
3. Synthesize voice with OpenAI TTS
4. Mix with background bed using ducking
5. Save to breaks directory

Implements producer pattern: only generates new breaks when needed.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .audio_mixer import mix_voice_with_bed
from .config import config
from .news import get_news
from .script_writer import generate_bulletin
from .voice_synth import synthesize_bulletin
from .weather import get_weather

logger = logging.getLogger(__name__)


@dataclass
class GeneratedBreak:
    """Generated radio break with metadata."""

    file_path: Path  # Path to final mixed audio file
    duration: float  # Duration in seconds
    timestamp: datetime
    includes_weather: bool
    includes_news: bool
    script_text: str  # Original bulletin script


class BreakGenerator:
    """Radio break generator orchestrator.

    Coordinates the full pipeline from data collection to final mixed audio:
    - Weather data (NWS)
    - News headlines (RSS)
    - Script generation (Claude)
    - Voice synthesis (OpenAI TTS)
    - Audio mixing with bed (ffmpeg)
    """

    def __init__(self):
        """Initialize break generator with config paths."""
        self.breaks_path = config.breaks_path
        self.beds_path = config.beds_path
        self.tmp_path = config.tmp_path
        self.freshness_minutes = config.break_freshness_minutes

    def _select_random_bed(self) -> Optional[Path]:
        """Select random background bed file from beds directory.

        Returns:
            Path to selected bed file, or None if no beds available
        """
        if not self.beds_path.exists():
            logger.error(f"Beds directory not found: {self.beds_path}")
            return None

        # Find all MP3 files in beds directory
        bed_files = list(self.beds_path.glob("*.mp3"))

        if not bed_files:
            logger.error(f"No bed files found in {self.beds_path}")
            return None

        # Select random bed
        selected_bed = random.choice(bed_files)
        logger.info(f"Selected bed file: {selected_bed.name}")

        return selected_bed

    def generate(self) -> Optional[GeneratedBreak]:
        """Generate complete radio break from scratch.

        Executes full pipeline:
        1. Fetch weather and news data
        2. Generate bulletin script
        3. Synthesize voice
        4. Mix with random bed
        5. Save to breaks directory

        Returns:
            GeneratedBreak with metadata, or None if generation fails
        """
        logger.info("Starting break generation pipeline")

        # Step 1: Collect data
        logger.info("Fetching weather and news data")
        weather = get_weather()
        news = get_news()

        if not weather and not news:
            logger.error("No weather or news data available")
            return None

        logger.info(
            f"Data collected: weather={'✓' if weather else '✗'}, "
            f"news={'✓' if news else '✗'}"
        )

        # Step 2: Generate script
        logger.info("Generating bulletin script with Claude")
        bulletin = generate_bulletin(weather=weather, news=news)

        if not bulletin:
            logger.error("Failed to generate bulletin script")
            return None

        logger.info(f"Script generated: {bulletin.word_count} words")

        # Step 3: Synthesize voice
        logger.info("Synthesizing voice with OpenAI TTS")

        # Ensure tmp directory exists
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        # Generate unique voice filename
        voice_filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        voice_path = self.tmp_path / voice_filename

        voice_audio = synthesize_bulletin(bulletin.script_text, voice_path)

        if not voice_audio:
            logger.error("Failed to synthesize voice")
            return None

        logger.info(f"Voice synthesized: {voice_audio.duration_estimate:.1f}s")

        # Step 4: Select random bed
        bed_path = self._select_random_bed()

        if not bed_path:
            logger.error("No bed file available for mixing")
            return None

        # Step 5: Mix voice with bed
        logger.info(f"Mixing voice with bed: {bed_path.name}")

        # Ensure breaks directory exists
        self.breaks_path.mkdir(parents=True, exist_ok=True)

        # Generate unique output filename
        output_filename = f"break_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = self.breaks_path / output_filename

        mixed_audio = mix_voice_with_bed(
            voice_path=voice_path,
            bed_path=bed_path,
            output_path=output_path,
        )

        if not mixed_audio:
            logger.error("Failed to mix audio")
            return None

        logger.info(f"Break generated successfully: {output_path.name}")

        return GeneratedBreak(
            file_path=output_path,
            duration=mixed_audio.duration,
            timestamp=datetime.now(),
            includes_weather=bulletin.includes_weather,
            includes_news=bulletin.includes_news,
            script_text=bulletin.script_text,
        )


def generate_break() -> Optional[GeneratedBreak]:
    """Convenience function to generate radio break.

    Returns:
        GeneratedBreak or None if generation fails
    """
    generator = BreakGenerator()
    return generator.generate()
