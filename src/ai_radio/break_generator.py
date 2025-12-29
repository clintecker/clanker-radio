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
        self.breaks_path = config.paths.breaks_path
        self.beds_path = config.paths.beds_path
        self.tmp_path = config.paths.tmp_path
        self.freshness_minutes = config.break_freshness_minutes

    def _select_random_bed(self) -> Optional[Path]:
        """Select random background bed file from beds directory.

        Returns:
            Path to selected bed file, or None if no beds available
        """
        if not self.beds_path.exists():
            logger.error(f"Beds directory not found: {self.beds_path}")
            return None

        # Find all audio files in beds directory (MP3 or WAV)
        bed_files = list(self.beds_path.glob("*.mp3")) + list(self.beds_path.glob("*.wav"))

        if not bed_files:
            logger.error(f"No bed files found in {self.beds_path}")
            return None

        # Select random bed
        selected_bed = random.choice(bed_files)
        logger.info(f"Selected bed file: {selected_bed.name}")

        return selected_bed

    def _archive_old_breaks(self, keep: int = 100, archive_keep: int = 500) -> None:
        """Keep the most recent breaks and archive the rest, deleting very old archived breaks.

        Args:
            keep: Number of recent breaks to keep in active directory
            archive_keep: Number of breaks to keep in archive before deleting
        """
        try:
            # Ensure archive directory exists
            archive_path = config.paths.breaks_archive_path
            archive_path.mkdir(parents=True, exist_ok=True)

            # Get all breaks, sorted by creation time (newest first)
            breaks = sorted(
                self.breaks_path.glob("break_*.mp3"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Archive older breaks beyond the keep limit
            if len(breaks) > keep:
                for old_break in breaks[keep:]:
                    archive_dest = archive_path / old_break.name
                    old_break.rename(archive_dest)
                    logger.info(f"Archived old break: {old_break.name}")

            # Clean up very old archived breaks
            archived_breaks = sorted(
                archive_path.glob("break_*.mp3"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if len(archived_breaks) > archive_keep:
                for very_old_break in archived_breaks[archive_keep:]:
                    very_old_break.unlink()
                    logger.info(f"Deleted very old archived break: {very_old_break.name}")

        except Exception as e:
            logger.warning(f"Failed to archive old breaks: {e}")

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
        # Clean up any orphaned temp files from previous failed runs
        cleanup_old_temp_files(max_age_minutes=60)

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
        logger.info("Synthesizing voice with TTS")

        # Ensure tmp directory exists
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        # Generate unique voice filename
        voice_filename = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        voice_path = self.tmp_path / voice_filename

        try:
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

            # Generate unique output filename and metadata
            # Use station timezone for metadata title (Chicago time)
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(config.station_tz))
            output_filename = f"break_{now.strftime('%Y%m%d_%H%M%S')}.mp3"
            output_path = self.breaks_path / output_filename

            # Round up to next hour for air time (matches spoken intro)
            # If generated at 3:52 PM, will air at 4:00 PM
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

            # Format title as "Mon Dec 29, 2025 4 PM News Break"
            # Show hour only (no minutes) since it airs on the hour
            hour_12 = next_hour.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "AM" if next_hour.hour < 12 else "PM"

            metadata_title = next_hour.strftime(f"%a %b %d, %Y {hour_12} {am_pm} News Break")

            mixed_audio = mix_voice_with_bed(
                voice_path=voice_path,
                bed_path=bed_path,
                output_path=output_path,
                metadata_title=metadata_title,
                metadata_artist=config.music_artist,
            )

            if not mixed_audio:
                logger.error("Failed to mix audio")
                return None

            logger.info(f"Break generated successfully: {output_path.name}")

            # Archive old breaks to prevent disk space exhaustion
            self._archive_old_breaks(keep=100)

            return GeneratedBreak(
                file_path=output_path,
                duration=mixed_audio.duration,
                timestamp=datetime.now(),
                includes_weather=bulletin.includes_weather,
                includes_news=bulletin.includes_news,
                script_text=bulletin.script_text,
            )

        finally:
            # Always clean up temporary voice file
            if voice_path.exists():
                voice_path.unlink()
                logger.debug(f"Cleaned up temporary voice file: {voice_path.name}")


def cleanup_old_temp_files(max_age_minutes: int = 60) -> int:
    """Clean up orphaned temporary files older than specified age.

    Args:
        max_age_minutes: Maximum age in minutes for temp files before deletion

    Returns:
        Number of files cleaned up
    """
    from time import time

    tmp_path = config.paths.tmp_path
    if not tmp_path.exists():
        return 0

    current_time = time()
    max_age_seconds = max_age_minutes * 60
    cleaned_count = 0

    try:
        for temp_file in tmp_path.glob("voice_*.mp3"):
            file_age = current_time - temp_file.stat().st_mtime
            if file_age > max_age_seconds:
                temp_file.unlink()
                cleaned_count += 1
                logger.info(f"Cleaned up old temp file: {temp_file.name} (age: {file_age/60:.1f}min)")
    except Exception as e:
        logger.warning(f"Failed to clean up temp files: {e}")

    return cleaned_count


def generate_break() -> Optional[GeneratedBreak]:
    """Convenience function to generate radio break.

    Returns:
        GeneratedBreak or None if generation fails
    """
    generator = BreakGenerator()
    return generator.generate()
