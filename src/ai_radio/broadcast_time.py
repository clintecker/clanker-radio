"""Which top-of-the-hour a news break belongs to.

Breaks are normally generated around :50 and air at the next top of the hour, but the
break-gen timer also catches up after a reboot or a manual restart, so a break can be
produced a few minutes *after* the hour and air right away. Rounding to the nearest hour
covers both: 3:52 -> 4:00, 4:01 -> 4:00, 4:29 -> 4:00, 4:31 -> 5:00.
"""
from datetime import datetime, timedelta


def broadcast_hour(now: datetime) -> datetime:
    """Top of the hour nearest to ``now`` (ties at :30 round up), timezone preserved."""
    top = now.replace(minute=0, second=0, microsecond=0)
    return top + timedelta(hours=1) if now - top >= timedelta(minutes=30) else top


def spoken_hour(hour: datetime) -> str:
    """'midnight', 'noon', or e.g. '4 pm'."""
    if hour.hour == 0:
        return "midnight"
    if hour.hour == 12:
        return "noon"
    h12 = hour.hour % 12 or 12
    return f"{h12} {'am' if hour.hour < 12 else 'pm'}"
