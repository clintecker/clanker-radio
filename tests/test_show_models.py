"""Tests for scheduled show models."""
import json
import pytest
from datetime import datetime
from ai_radio.show_models import ShowSchedule


def test_create_show_schedule(tmp_path):
    """Test creating a ShowSchedule with all required fields."""
    schedule = ShowSchedule(
        name="Crypto Morning Show",
        format="two_host_discussion",
        topic_area="Bitcoin and DeFi news",
        days_of_week=json.dumps([1, 2, 3, 4, 5]),  # M-F
        start_time="09:00",
        duration_minutes=8,
        timezone="America/New_York",
        personas=json.dumps([
            {"name": "Marco", "traits": "skeptical, data-driven"},
            {"name": "Chloe", "traits": "optimistic, long-term"}
        ]),
        content_guidance="Latest crypto news and market analysis",
        regenerate_daily=True,
        active=True
    )

    assert schedule.name == "Crypto Morning Show"
    assert schedule.format == "two_host_discussion"
    assert json.loads(schedule.days_of_week) == [1, 2, 3, 4, 5]
    assert schedule.active is True


def test_create_generated_show():
    """Test creating a GeneratedShow with all required fields."""
    from ai_radio.show_models import GeneratedShow

    show = GeneratedShow(
        schedule_id=1,
        air_date="2026-01-18",
        status="pending",
        retry_count=0,
        script_text=None,
        asset_id=None,
        generated_at=None,
        error_message=None
    )

    assert show.schedule_id == 1
    assert show.air_date == "2026-01-18"
    assert show.status == "pending"
    assert show.retry_count == 0
