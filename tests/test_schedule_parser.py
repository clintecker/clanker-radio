"""Tests for natural language schedule parsing."""
import pytest
from ai_radio.schedule_parser import ScheduleParser


def test_parse_simple_schedule():
    """Test parsing a basic schedule description."""
    parser = ScheduleParser()

    result = parser.parse(
        "Monday through Friday at 9am, two hosts discuss Bitcoin and DeFi news"
    )

    assert result.name is not None
    assert result.format == "two_host_discussion"
    assert result.topic_area == "Bitcoin and DeFi news"
    assert 1 in result.days_of_week  # Monday
    assert 5 in result.days_of_week  # Friday
    assert result.start_time == "09:00"
    assert len(result.personas) == 2
