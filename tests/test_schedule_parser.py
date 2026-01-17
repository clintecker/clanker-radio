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


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_invalid_json(mock_client_class):
    """Test handling of invalid JSON response."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "This is not valid JSON at all!"
    mock_client.models.generate_content.return_value = mock_response

    parser = ScheduleParser()
    with pytest.raises(ValueError, match="Invalid JSON response from Gemini"):
        parser.parse("Some schedule description")


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_missing_required_fields(mock_client_class):
    """Test handling of response with missing required fields."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''{
        "name": "Test Show",
        "format": "interview"
    }'''
    mock_client.models.generate_content.return_value = mock_response

    parser = ScheduleParser()
    with pytest.raises(ValueError, match="Response missing required fields"):
        parser.parse("Some schedule description")


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_api_failure(mock_client_class):
    """Test handling of API call failure."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.models.generate_content.side_effect = Exception("API Error")

    parser = ScheduleParser()
    with pytest.raises(RuntimeError, match="Failed to parse schedule"):
        parser.parse("Some schedule description")


@patch('ai_radio.schedule_parser.config')
def test_init_missing_api_key(mock_config):
    """Test initialization with missing API key."""
    mock_config.api_keys.gemini_api_key = None

    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        ScheduleParser()


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_empty_input(mock_client_class):
    """Test parsing with empty input."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    parser = ScheduleParser()
    with pytest.raises(ValueError, match="Cannot parse empty schedule description"):
        parser.parse("")

    with pytest.raises(ValueError, match="Cannot parse empty schedule description"):
        parser.parse("   ")


@patch('ai_radio.schedule_parser.genai.Client')
def test_parse_input_too_long(mock_client_class):
    """Test parsing with input that exceeds length limit."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    parser = ScheduleParser()
    long_input = "x" * 2001
    with pytest.raises(ValueError, match="Schedule description too long"):
        parser.parse(long_input)
