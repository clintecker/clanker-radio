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
            return 0
        else:
            logger.error("Break generation failed")
            return 1

    except Exception as e:
        logger.exception(f"Unexpected error during break generation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
