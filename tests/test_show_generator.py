"""Tests for show generation pipeline."""
import pytest
from unittest.mock import Mock, patch
from ai_radio.show_generator import research_topics


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics(mock_client_class):
    """Test researching topics for a show."""
    # Mock the Gemini API response
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '''[
        "Bitcoin reaches new all-time high above $100,000",
        "SEC approves multiple Bitcoin ETFs for retail investors",
        "DeFi protocols see surge in total value locked"
    ]'''
    mock_client.models.generate_content.return_value = mock_response

    topics = research_topics(
        topic_area="Bitcoin news",
        content_guidance="Latest price movements and regulatory updates"
    )

    assert isinstance(topics, list)
    assert len(topics) > 0
    assert all(isinstance(t, str) for t in topics)
    assert len(topics) == 3


def test_research_topics_empty_input():
    """Test that empty topic_area raises ValueError."""
    with pytest.raises(ValueError, match="Cannot research topics without a topic area"):
        research_topics("")

    with pytest.raises(ValueError, match="Cannot research topics without a topic area"):
        research_topics("   ")


def test_research_topics_input_too_long():
    """Test that topic_area longer than 500 chars raises ValueError."""
    long_topic = "a" * 501
    with pytest.raises(ValueError, match="Topic area too long"):
        research_topics(long_topic)


def test_research_topics_content_guidance_too_long():
    """Test that content_guidance longer than 1000 chars raises ValueError."""
    long_guidance = "a" * 1001
    with pytest.raises(ValueError, match="Content guidance too long"):
        research_topics("Bitcoin news", content_guidance=long_guidance)


@patch('ai_radio.show_generator.config')
def test_research_topics_missing_api_key(mock_config):
    """Test that missing API key raises ValueError."""
    mock_config.api_keys.gemini_api_key = None
    with pytest.raises(ValueError, match="RADIO_GEMINI_API_KEY not configured"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_invalid_json(mock_client_class):
    """Test that malformed JSON response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = "This is not valid JSON"
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Invalid JSON response from Gemini"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_not_a_list(mock_client_class):
    """Test that non-list response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '{"error": "not a list"}'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Response is not a list"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_empty_list(mock_client_class):
    """Test that empty list response raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '[]'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="No topics returned"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_non_string_items(mock_client_class):
    """Test that list with non-string items raises ValueError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_response = Mock()
    mock_response.text = '[1, 2, 3]'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(ValueError, match="Not all topics are strings"):
        research_topics("Bitcoin news")


@patch('ai_radio.show_generator.genai.Client')
def test_research_topics_api_failure(mock_client_class):
    """Test that general API error raises RuntimeError."""
    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mock_client.models.generate_content.side_effect = Exception("API connection failed")

    with pytest.raises(RuntimeError, match="Failed to research topics"):
        research_topics("Bitcoin news")
