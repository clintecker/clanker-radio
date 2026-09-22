"""Tests for the pure show scheduling helpers."""
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from ai_radio.show_models import ShowSchedule
from ai_radio.show_scheduling import air_dates_needing_generation, next_air_datetime


def make_schedule(days=(0, 1, 2, 3, 4, 5, 6), start="15:30", tz="US/Eastern"):
    return ShowSchedule(
        name="The AI Report", format="interview", topic_area="AI",
        days_of_week=json.dumps(list(days)), start_time=start, duration_minutes=8,
        timezone=tz, personas="[]", content_guidance=None, regenerate_daily=True,
        active=True, id=1,
    )


def test_next_air_is_today_when_before_start_time():
    now = datetime(2026, 9, 22, 12, 0, tzinfo=ZoneInfo("US/Eastern"))
    nxt = next_air_datetime(make_schedule(), now)
    assert nxt == datetime(2026, 9, 22, 15, 30, tzinfo=ZoneInfo("US/Eastern"))


def test_next_air_rolls_to_tomorrow_after_start_time():
    now = datetime(2026, 9, 22, 15, 31, tzinfo=ZoneInfo("US/Eastern"))
    assert next_air_datetime(make_schedule(), now).date() == date(2026, 9, 23)


def test_next_air_at_exact_start_time_is_today():
    now = datetime(2026, 9, 22, 15, 30, tzinfo=ZoneInfo("US/Eastern"))
    assert next_air_datetime(make_schedule(), now).date() == date(2026, 9, 22)


def test_next_air_skips_disabled_weekdays():
    # 2026-09-22 is a Tuesday (weekday 1); schedule only airs Fridays (4).
    now = datetime(2026, 9, 22, 12, 0, tzinfo=ZoneInfo("US/Eastern"))
    assert next_air_datetime(make_schedule(days=(4,)), now).date() == date(2026, 9, 25)


def test_next_air_converts_utc_now_into_schedule_timezone():
    # 19:00 UTC on Sep 22 is 15:00 Eastern: still before the 15:30 show.
    now = datetime(2026, 9, 22, 19, 0, tzinfo=timezone.utc)
    nxt = next_air_datetime(make_schedule(), now)
    assert nxt.date() == date(2026, 9, 22)
    assert nxt.utcoffset() == timedelta(hours=-4)


def test_no_days_enabled_raises():
    now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        next_air_datetime(make_schedule(days=()), now)


def test_generation_due_inside_lead_window():
    now = datetime(2026, 9, 22, 10, 0, tzinfo=ZoneInfo("US/Eastern"))  # 5.5h before air
    assert air_dates_needing_generation(make_schedule(), now, timedelta(hours=6)) == [date(2026, 9, 22)]


def test_generation_not_due_outside_lead_window():
    now = datetime(2026, 9, 22, 8, 0, tzinfo=ZoneInfo("US/Eastern"))  # 7.5h before air
    assert air_dates_needing_generation(make_schedule(), now, timedelta(hours=6)) == []


def test_generation_after_todays_airing_targets_tomorrow_only_when_close():
    now = datetime(2026, 9, 22, 16, 0, tzinfo=ZoneInfo("US/Eastern"))  # 23.5h before next
    assert air_dates_needing_generation(make_schedule(), now, timedelta(hours=6)) == []
    assert air_dates_needing_generation(make_schedule(), now, timedelta(hours=24)) == [date(2026, 9, 23)]
