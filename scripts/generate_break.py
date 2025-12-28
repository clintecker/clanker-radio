#!/usr/bin/env python3
"""Content generation service script.

Generates radio breaks on demand by orchestrating the full pipeline:
- Fetch weather and news data
- Generate bulletin script with Claude
- Synthesize voice with OpenAI TTS
- Mix with background bed
- Save to breaks directory

Designed to be called by systemd timer for automatic break generation.

Usage:
    ./scripts/generate_break.py

Exit codes:
    0: Break generated successfully
    1: Break generation failed
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.break_generator import generate_break
from ai_radio.config import config
from ai_radio.ingest import ingest_audio_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main() -> int:
    """Generate radio break and return exit code.

    Returns:
        0 if successful, 1 if failed
    """
    logger.info("Starting break generation service")

    try:
        result = generate_break()

        if result:
            logger.info(
                f"Break generated successfully: {result.file_path.name} "
                f"({result.duration:.1f}s, "
                f"weather={result.includes_weather}, "
                f"news={result.includes_news})"
            )

            # Auto-ingest break immediately
            try:
                logger.info("📥 Auto-ingesting break into assets table...")
                ingest_audio_file(
                    source_path=result.file_path,
                    kind="break",
                    db_path=config.db_path,
                    ingest_existing=True,
                )
                logger.info("✅ Break ingested successfully")
            except Exception as e:
                logger.error(f"❌ Failed to ingest break: {e}")
                return 1  # Fail loudly for systemd alerting

            return 0
        else:
            logger.error("Break generation failed")
            return 1

    except Exception as e:
        logger.exception(f"Unexpected error during break generation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
