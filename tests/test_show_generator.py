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
