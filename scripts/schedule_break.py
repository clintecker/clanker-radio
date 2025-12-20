#!/usr/bin/env python3
"""
AI Radio Station - Break Scheduler
Pushes breaks to Liquidsoap at top of hour
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.liquidsoap_client import LiquidsoapClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

QUEUE_NAME = "breaks"


def main():
    """Main entry point"""
    now = datetime.now()

    # Check if we're within 5 minutes of the hour
    minutes = now.minute

    if minutes >= 5:
        logger.info(f"Not near top of hour (minute: {minutes}), skipping")
        sys.exit(0)

    logger.info("Near top of hour, scheduling break...")

    # Check if break already queued (prevent double-scheduling)
    client = LiquidsoapClient()
    if client.get_queue_length(QUEUE_NAME) > 0:
        logger.info("Break already queued, skipping")
        sys.exit(0)

    # Find next.mp3 (SOW-mandated file)
    breaks_dir = config.breaks_path
    next_break = breaks_dir / "next.mp3"

    if not next_break.exists():
        logger.warning(f"No break available: {next_break}")

        # Try last_good.mp3 fallback (SOW Section 9)
        last_good = breaks_dir / "last_good.mp3"
        if last_good.exists():
            logger.info("Using last_good.mp3 fallback")
            next_break = last_good
        else:
            logger.error("No breaks available (neither next.mp3 nor last_good.mp3)")
            sys.exit(1)

    # Push to Liquidsoap break queue
    if client.push_track(QUEUE_NAME, str(next_break)):
        logger.info(f"Break scheduled: {next_break}")
        sys.exit(0)
    else:
        logger.error("Failed to schedule break")
        sys.exit(1)


if __name__ == "__main__":
    main()
