"""Tests for natural language schedule parsing."""
import pytest
from unittest.mock import Mock, patch
from ai_radio.schedule_parser import ScheduleParser


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_simple_schedule(mock_client_class):
    """Test parsing a basic schedule description."""
    # Mock the Gemini API response
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''{
        "name": "Crypto Morning Discussion",
        "format": "two_host_discussion",
        "topic_area": "Bitcoin and DeFi news",
        "days_of_week": [1, 2, 3, 4, 5],
        "start_time": "09:00",
        "duration_minutes": 8,
        "personas": [
            {"name": "Alex", "traits": "analytical, skeptical"},
            {"name": "Jordan", "traits": "optimistic, forward-thinking"}
        ],
        "content_guidance": "Latest developments in cryptocurrency"
    }'''
    mock_client.models.generate_content.return_value = mock_response

    parser = ScheduleParser()
    result = parser.parse(
        "Monday through Friday at 9am, two hosts discuss Bitcoin and DeFi news"
    )

    assert result.name is not None
    assert result.format == "two_host_discussion"
    assert "Bitcoin" in result.topic_area and "DeFi" in result.topic_area
    assert 1 in result.days_of_week  # Monday
    assert 5 in result.days_of_week  # Friday
    assert result.start_time == "09:00"
    assert len(result.personas) == 2
