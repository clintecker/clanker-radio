#!/usr/bin/env python3
"""Schedule station ID bumpers at designated times.

Picks a random existing station ID file and queues it to play at the next
track boundary at :15, :30, and :45 minutes past each hour.
"""
import logging
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.liquidsoap_client import LiquidsoapClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STATION_ID_TIMES = [15, 30, 45]  # Minutes when station IDs should play
TIME_WINDOW = 2  # Minutes before target time to start scheduling
STATE_FILE = config.state_path / "last_station_id_scheduled.txt"


def should_schedule_station_id() -> tuple[bool, int | None]:
    """Check if we should schedule a station ID now.

    Returns:
        (should_schedule, target_minute): Whether to schedule and which minute target
    """
    now = datetime.now(ZoneInfo(config.station_tz))
    current_minute = now.minute

    # Find the next target minute
    for target in STATION_ID_TIMES:
        # Schedule within TIME_WINDOW minutes before target
        if target - TIME_WINDOW <= current_minute < target:
            # Check if we already scheduled for this target
            if STATE_FILE.exists():
                try:
                    last_scheduled = int(STATE_FILE.read_text().strip())
                    if last_scheduled == target:
                        logger.info(f"Station ID already scheduled for :{target:02d}")
                        return False, None
                except (ValueError, FileNotFoundError):
                    pass

            logger.info(f"Should schedule station ID for :{target:02d} (current: :{current_minute:02d})")
            return True, target

    # Clear state if we're past all targets or before the first window
    if current_minute >= max(STATION_ID_TIMES) or current_minute < (min(STATION_ID_TIMES) - TIME_WINDOW):
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    return False, None


def get_random_station_id() -> Path | None:
    """Pick a random station ID file from the bumpers directory.

    Returns:
        Path to random station ID file, or None if no files found
    """
    bumpers_path = config.base_path / "assets" / "bumpers"

    if not bumpers_path.exists():
        logger.error(f"Bumpers directory not found: {bumpers_path}")
        return None

    # Get all station ID files (both .wav and .mp3)
    station_ids = list(bumpers_path.glob("station_id_*.wav")) + list(bumpers_path.glob("station_id_*.mp3"))

    if not station_ids:
        logger.error(f"No station ID files found in {bumpers_path}")
        return None

    # Pick a random one
    selected = random.choice(station_ids)
    return selected


def main():
    """Entry point"""
    try:
        # Ensure state directory exists
        config.state_path.mkdir(parents=True, exist_ok=True)

        # Check if we should schedule
        should_schedule, target_minute = should_schedule_station_id()

        if not should_schedule:
            logger.info("No station ID scheduling needed at this time")
            sys.exit(0)

        # Pick a random station ID file
        station_id_file = get_random_station_id()

        if not station_id_file:
            logger.error("Failed to find station ID file")
            sys.exit(1)

        logger.info(f"Selected random station ID: {station_id_file.name}")

        # Queue it to the breaks queue (which respects track boundaries)
        client = LiquidsoapClient()

        if client.push_track("breaks", str(station_id_file)):
            logger.info(f"Queued station ID: {station_id_file.name}")

            # Record that we scheduled for this target
            STATE_FILE.write_text(str(target_minute))

            sys.exit(0)
        else:
            logger.error("Failed to queue station ID")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Station ID scheduling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
