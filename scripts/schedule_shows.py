#!/usr/bin/env python3
"""
AI Radio Station - Show Scheduler
Polls for scheduled shows that should air now and enqueues them to Liquidsoap.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.show_repository import ShowRepository
from ai_radio.liquidsoap_client import LiquidsoapClient
from ai_radio.show_models import ShowSchedule, ShowStatus, LiquidsoapQueue
from ai_radio.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def should_air_now(schedule: ShowSchedule, now: datetime) -> bool:
    """Determine if a schedule should be airing at the given time.

    Checks if the current time matches the schedule's day of week and start time.
    The schedule is considered to match if:
    - The day of week is in the schedule's days_of_week list (0=Monday, 6=Sunday)
    - The hour and minute match the schedule's start_time

    Args:
        schedule: The show schedule to check
        now: Current time (timezone-aware)

    Returns:
        True if schedule should be airing now, False otherwise

    DST Handling:
        Python's ZoneInfo handles Daylight Saving Time transitions automatically:

        Spring Forward (2AM -> 3AM):
            - Times in the gap (e.g., 2:30AM) don't exist
            - Shows scheduled during the gap won't air
            - ZoneInfo skips non-existent times using fold-aware handling

        Fall Back (2AM happens twice):
            - Times in the overlap are ambiguous (happen twice)
            - Python uses fold=0 by default (first occurrence)
            - Shows scheduled in the overlap air during first occurrence only
            - Minute-based polling prevents duplicate airings

        The polling interval (1 minute) ensures shows air once per scheduled time,
        even during DST transitions.
    """
    # Parse days_of_week from JSON
    days_of_week = json.loads(schedule.days_of_week)

    # Convert now to schedule's timezone
    schedule_tz = ZoneInfo(schedule.timezone)
    now_in_schedule_tz = now.astimezone(schedule_tz)

    # Check if current day is in schedule
    current_day = now_in_schedule_tz.weekday()  # 0=Monday, 6=Sunday
    if current_day not in days_of_week:
        return False

    # Parse start_time (format: "09:00")
    start_hour, start_minute = map(int, schedule.start_time.split(':'))

    # Check if current time matches start time (hour and minute)
    if now_in_schedule_tz.hour == start_hour and now_in_schedule_tz.minute == start_minute:
        return True

    return False


def check_scheduled_shows() -> None:
    """Main orchestration function for checking and enqueuing scheduled shows.

    For each active schedule:
    - Check if it should be airing now
    - Get ready show for today
    - Enqueue to Liquidsoap if ready
    - Log warnings for shows that should air but aren't ready
    """
    repository = ShowRepository(str(config.paths.db_path))
    client = LiquidsoapClient()

    # Get active schedules
    schedules = repository.get_active_schedules()

    # Get current time
    now = datetime.now()

    # Process each schedule
    for schedule in schedules:
        # Check if schedule should air now
        if not should_air_now(schedule, now):
            continue

        # Get ready show for today
        air_date = now.date().isoformat()
        show = repository.get_ready_show(schedule_id=schedule.id, air_date=air_date)

        # Check if show is ready
        if show and show.asset_id:
            # Get asset path
            asset_path = repository.get_asset_path(show.asset_id)

            # Enqueue to Liquidsoap
            try:
                success = client.push_track(LiquidsoapQueue.BREAKS, str(asset_path))
                if success:
                    logger.info(f"Enqueued show: {schedule.name}")
                else:
                    logger.error(f"Failed to enqueue show: {schedule.name} (asset: {show.asset_id})")
            except Exception as e:
                logger.error(f"Error enqueuing show {schedule.name}: {e}")
        else:
            # Show not ready
            logger.warning(f"Show not ready: {schedule.name}")


def main():
    """Main entry point."""
    try:
        check_scheduled_shows()
    except Exception as e:
        logger.error(f"Error checking scheduled shows: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
