#!/usr/bin/env python3
"""Schedule station ID bumpers at designated times.

Picks a random existing station ID file and queues it to play at the next
track boundary at :15, :30, and :45 minutes past each hour.
"""
import logging
import random
import sqlite3
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


def get_scheduler_state(conn: sqlite3.Connection, key: str) -> str | None:
    """Get scheduler state from database."""
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM scheduler_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def set_scheduler_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set scheduler state in database."""
    cursor = conn.cursor()
    now = datetime.now(ZoneInfo(config.station_tz)).isoformat()
    cursor.execute(
        """INSERT INTO scheduler_state (key, value, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?""",
        (key, value, now, value, now)
    )
    conn.commit()


def should_schedule_station_id(conn: sqlite3.Connection) -> tuple[bool, int | None]:
    """Check if we should schedule a station ID now.

    Schedules during the minute before target time (e.g., during minute :14 for :15 target).
    Uses database state to prevent duplicate scheduling across hour boundaries.

    Args:
        conn: Database connection

    Returns:
        (should_schedule, target_minute): Whether to schedule and which minute target
    """
    now = datetime.now(ZoneInfo(config.station_tz))
    current_minute = now.minute
    current_hour = now.hour

    # Check if we're in a scheduling window (one minute before any target)
    for target in STATION_ID_TIMES:
        schedule_minute = target - 1  # One minute before target

        if current_minute == schedule_minute:
            # Check if we already scheduled for this target in this hour
            state_key = f"station_id_scheduled"
            state_value = get_scheduler_state(conn, state_key)

            if state_value:
                try:
                    last_hour, last_target = state_value.split(":")
                    if int(last_hour) == current_hour and int(last_target) == target:
                        logger.info(f"Station ID already scheduled for {current_hour:02d}:{target:02d}")
                        return False, None
                except ValueError:
                    pass  # Corrupt state, proceed to schedule

            logger.info(f"Scheduling station ID for :{target:02d}")
            return True, target

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
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect(config.db_path)

        # Check if we should schedule
        should_schedule, target_minute = should_schedule_station_id(conn)

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

            # Record that we scheduled for this target in this hour (format: "hour:target")
            now = datetime.now(ZoneInfo(config.station_tz))
            set_scheduler_state(conn, "station_id_scheduled", f"{now.hour}:{target_minute}")

            sys.exit(0)
        else:
            logger.error("Failed to queue station ID")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Station ID scheduling failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
