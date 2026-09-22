"""Pure scheduling helpers for AI-generated shows.

Kept free of I/O so the date math can be unit tested without a database.
"""
import json
from datetime import date, datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from ai_radio.show_models import ShowSchedule


def next_air_datetime(schedule: ShowSchedule, now: datetime) -> datetime:
    """Return the next scheduled air time at or after ``now``.

    Args:
        schedule: Show schedule with days_of_week (JSON list, 0=Monday),
            start_time ("HH:MM") and an IANA timezone.
        now: Timezone-aware current time.

    Returns:
        Timezone-aware datetime in the schedule's timezone.

    Raises:
        ValueError: If the schedule has no days of the week enabled.
    """
    days = json.loads(schedule.days_of_week)
    if not days:
        raise ValueError(f"Schedule {schedule.name!r} has no days_of_week")

    tz = ZoneInfo(schedule.timezone)
    local_now = now.astimezone(tz)
    hour, minute = map(int, schedule.start_time.split(":"))

    for offset in range(8):
        candidate_day = local_now.date() + timedelta(days=offset)
        if candidate_day.weekday() not in days:
            continue
        candidate = datetime(
            candidate_day.year, candidate_day.month, candidate_day.day,
            hour, minute, tzinfo=tz,
        )
        if candidate >= local_now:
            return candidate

    # Unreachable: at least one weekday is enabled, so a match exists within 8 days.
    raise AssertionError("no air time found within a week")


def air_dates_needing_generation(
    schedule: ShowSchedule, now: datetime, lead: timedelta
) -> List[date]:
    """Air dates whose show must be generated now.

    A show is due for generation once its air time is within ``lead`` of ``now``.
    Only the next occurrence is ever returned; generating further ahead would
    make the content stale for a daily news-style show.

    Args:
        schedule: Show schedule.
        now: Timezone-aware current time.
        lead: How far ahead of air time generation should start.

    Returns:
        A list with zero or one air dates (schedule-local calendar dates).
    """
    upcoming = next_air_datetime(schedule, now)
    if upcoming - now.astimezone(upcoming.tzinfo) <= lead:
        return [upcoming.date()]
    return []
