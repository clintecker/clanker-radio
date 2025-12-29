#!/usr/bin/env python3
"""Generate and schedule custom radio break with provided script.

Usage:
    ./scripts/generate_custom_break.py "Your custom message here"

This will:
1. Synthesize the provided text to speech
2. Mix with a random background bed
3. Save to breaks directory
4. Queue it to play immediately via override queue
"""

import logging
import random
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.audio_mixer import mix_voice_with_bed
from ai_radio.config import config
from ai_radio.liquidsoap_client import LiquidsoapClient
from ai_radio.voice_synth import synthesize_bulletin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def select_random_bed() -> Path:
    """Select random background bed file."""
    beds_path = config.paths.beds_path
    bed_files = list(beds_path.glob("*.mp3")) + list(beds_path.glob("*.wav"))

    if not bed_files:
        raise RuntimeError(f"No bed files found in {beds_path}")

    bed = random.choice(bed_files)
    logger.info(f"Selected bed: {bed.name}")
    return bed


def generate_custom_break(script_text: str) -> Path:
    """Generate custom break with provided script.

    Args:
        script_text: The message to broadcast

    Returns:
        Path to generated break file
    """
    logger.info("Starting custom break generation")

    # Ensure tmp directory exists
    tmp_path = config.paths.tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)

    # Generate voice
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    voice_path = tmp_path / f"voice_custom_{timestamp}.mp3"

    logger.info("Synthesizing voice...")
    voice_audio = synthesize_bulletin(script_text, voice_path)

    if not voice_audio:
        raise RuntimeError("Voice synthesis failed")

    logger.info(f"Voice synthesized: {voice_audio.duration_estimate:.1f}s")

    try:
        # Select bed and mix
        bed_path = select_random_bed()

        # Ensure breaks directory exists
        breaks_path = config.paths.breaks_path
        breaks_path.mkdir(parents=True, exist_ok=True)

        output_path = breaks_path / f"custom_break_{timestamp}.mp3"

        logger.info("Mixing voice with bed...")
        mixed_audio = mix_voice_with_bed(
            voice_path=voice_path,
            bed_path=bed_path,
            output_path=output_path,
        )

        if not mixed_audio:
            raise RuntimeError("Audio mixing failed")

        logger.info(f"Break generated: {output_path.name} ({mixed_audio.duration:.1f}s)")
        return output_path

    finally:
        # Clean up temp voice file
        if voice_path.exists():
            voice_path.unlink()


def schedule_break(break_path: Path) -> bool:
    """Schedule break to play immediately via override queue.

    Args:
        break_path: Path to break audio file

    Returns:
        True if scheduled successfully
    """
    logger.info("Scheduling break to override queue (plays immediately)...")

    client = LiquidsoapClient()
    success = client.push_track("override", break_path)

    if success:
        logger.info("✓ Break scheduled to override queue (plays after current track)")
        return True
    else:
        logger.error("✗ Failed to schedule break")
        return False


def main() -> int:
    """Generate and schedule custom break."""
    if len(sys.argv) < 2:
        print("Usage: ./scripts/generate_custom_break.py 'Your message here'")
        return 1

    script_text = " ".join(sys.argv[1:])

    try:
        # Generate break
        break_path = generate_custom_break(script_text)

        # Schedule to play
        if schedule_break(break_path):
            print(f"\n✓ Custom break generated and scheduled!")
            print(f"  File: {break_path.name}")
            print(f"  Queue: override (plays after current track ends)")
            return 0
        else:
            return 1

    except Exception as e:
        logger.exception(f"Failed to generate custom break: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
