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

from ai_radio.break_scheduler import get_fresh_break, StaleBreakError
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

    # Schedule during minute :59 for :00 top-of-hour break
    # (Same pattern as station IDs: schedule 1 minute before target)
    minutes = now.minute

    if minutes != 59:
        logger.info(f"Not at :59 minute (current: {minutes}), skipping")
        sys.exit(0)

    logger.info("At :59, scheduling break for top of hour...")

    # Check if break already queued (prevent double-scheduling)
    client = LiquidsoapClient()
    if client.get_queue_length(QUEUE_NAME) > 0:
        logger.info("Break already queued, skipping")
        sys.exit(0)

    # Find most recent fresh break
    try:
        next_break = get_fresh_break()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except StaleBreakError as e:
        logger.error(str(e))
        sys.exit(1)

    # Final existence check to minimize TOCTOU race window
    # (file could still be deleted after this check, but push_track will handle gracefully)
    if not next_break.exists():
        logger.error(f"Break file disappeared before push: {next_break}")
        sys.exit(1)

    # Push to Liquidsoap break queue
    if client.push_track(QUEUE_NAME, str(next_break)):
        logger.info(f"Break scheduled: {next_break}")
        sys.exit(0)
    else:
        logger.error(f"Failed to schedule break: {next_break}")
        sys.exit(1)


if __name__ == "__main__":
    main()
