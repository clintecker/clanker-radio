"""Tests for Claude-powered bulletin script generation.

Test coverage:
- Successful bulletin generation (weather + news)
- Weather-only bulletins
- News-only bulletins
- API error handling
- Missing API key handling
- Empty data handling
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from anthropic import APIError

from ai_radio.news import NewsData, NewsHeadline
from ai_radio.script_writer import ClaudeScriptWriter, BulletinScript, generate_bulletin
from ai_radio.weather import WeatherData


class TestClaudeScriptWriter:
    """Tests for ClaudeScriptWriter."""

    def test_initialization_requires_api_key(self):
        """ClaudeScriptWriter should raise ValueError if API key not configured."""
        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = None

            with pytest.raises(ValueError, match="RADIO_LLM_API_KEY not configured"):
                ClaudeScriptWriter()

    def test_initialization_with_api_key(self):
        """ClaudeScriptWriter should initialize with valid API key."""
        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-api-key"

            writer = ClaudeScriptWriter()

            assert writer.api_key == "test-api-key"
            assert writer.model == "claude-3-5-sonnet-20241022"
            assert writer.max_tokens == 512

    def test_generate_bulletin_weather_and_news(self):
        """generate_bulletin should create script from weather and news data."""
        weather = WeatherData(
            temperature=68,
            conditions="Sunny",
            forecast_short="Clear skies expected through the afternoon.",
            timestamp=datetime.now(),
        )

        news = NewsData(
            headlines=[
                NewsHeadline(
                    title="Local event attracts thousands",
                    source="Local News",
                    link="https://example.com/1",
                ),
                NewsHeadline(
                    title="City council approves budget",
                    source="Local News",
                    link="https://example.com/2",
                ),
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                # Mock Claude API response
                mock_response = Mock()
                mock_content = Mock()
                mock_content.text = "Good afternoon! You're listening to AI Radio. Currently it's 68 degrees and sunny with clear skies expected. In local news, a local event attracted thousands of visitors today. The city council has approved the new budget. Stay tuned for more!"
                mock_response.content = [mock_content]
                mock_client.messages.create.return_value = mock_response

                writer = ClaudeScriptWriter()
                bulletin = writer.generate_bulletin(weather, news)

                # Verify API call
                mock_client.messages.create.assert_called_once()
                call_kwargs = mock_client.messages.create.call_args[1]
                assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
                assert call_kwargs["max_tokens"] == 512
                assert "68°F" in call_kwargs["messages"][0]["content"]
                assert "Sunny" in call_kwargs["messages"][0]["content"]
                assert "Local event attracts thousands" in call_kwargs["messages"][0]["content"]

                # Verify bulletin
                assert bulletin is not None
                assert bulletin.includes_weather is True
                assert bulletin.includes_news is True
                assert bulletin.word_count > 0
                assert isinstance(bulletin.timestamp, datetime)
                assert "68 degrees" in bulletin.script_text.lower()

    def test_generate_bulletin_weather_only(self):
        """generate_bulletin should create weather-only bulletin."""
        weather = WeatherData(
            temperature=72,
            conditions="Partly Cloudy",
            forecast_short="Mild conditions throughout the day.",
            timestamp=datetime.now(),
        )

        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                mock_response = Mock()
                mock_content = Mock()
                mock_content.text = "Here's your weather update: it's 72 and partly cloudy with mild conditions expected today."
                mock_response.content = [mock_content]
                mock_client.messages.create.return_value = mock_response

                writer = ClaudeScriptWriter()
                bulletin = writer.generate_bulletin(weather=weather, news=None)

                assert bulletin is not None
                assert bulletin.includes_weather is True
                assert bulletin.includes_news is False

                # Verify prompt doesn't include news
                call_kwargs = mock_client.messages.create.call_args[1]
                assert "NEWS HEADLINES" not in call_kwargs["messages"][0]["content"]

    def test_generate_bulletin_news_only(self):
        """generate_bulletin should create news-only bulletin."""
        news = NewsData(
            headlines=[
                NewsHeadline(title="Breaking story", source="News", link="https://example.com/1")
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                mock_response = Mock()
                mock_content = Mock()
                mock_content.text = "In the news today: breaking story develops."
                mock_response.content = [mock_content]
                mock_client.messages.create.return_value = mock_response

                writer = ClaudeScriptWriter()
                bulletin = writer.generate_bulletin(weather=None, news=news)

                assert bulletin is not None
                assert bulletin.includes_weather is False
                assert bulletin.includes_news is True

                # Verify prompt doesn't include weather
                call_kwargs = mock_client.messages.create.call_args[1]
                assert "WEATHER" not in call_kwargs["messages"][0]["content"]

    def test_generate_bulletin_no_data(self):
        """generate_bulletin should return None when no data provided."""
        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            writer = ClaudeScriptWriter()
            bulletin = writer.generate_bulletin(weather=None, news=None)

            assert bulletin is None

    def test_generate_bulletin_api_error(self):
        """generate_bulletin should return None on API error."""
        weather = WeatherData(
            temperature=60,
            conditions="Rainy",
            forecast_short="Rain expected.",
            timestamp=datetime.now(),
        )

        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                # Simulate API error with proper request mock
                mock_request = Mock()
                mock_client.messages.create.side_effect = APIError(
                    "API rate limit", body=None, request=mock_request
                )

                writer = ClaudeScriptWriter()
                bulletin = writer.generate_bulletin(weather=weather)

                assert bulletin is None

    def test_generate_bulletin_limits_headlines(self):
        """generate_bulletin should limit to 3 headlines in prompt."""
        news = NewsData(
            headlines=[
                NewsHeadline(title=f"Story {i}", source="News", link=f"https://example.com/{i}")
                for i in range(10)  # 10 headlines
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        with patch("ai_radio.script_writer.config") as mock_config:
            mock_config.llm_api_key = "test-key"

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                mock_response = Mock()
                mock_content = Mock()
                mock_content.text = "News bulletin script"
                mock_response.content = [mock_content]
                mock_client.messages.create.return_value = mock_response

                writer = ClaudeScriptWriter()
                writer.generate_bulletin(news=news)

                # Verify only 3 headlines in prompt
                call_kwargs = mock_client.messages.create.call_args[1]
                prompt = call_kwargs["messages"][0]["content"]
                assert "Story 0" in prompt
                assert "Story 1" in prompt
                assert "Story 2" in prompt
                assert "Story 3" not in prompt  # Should not include 4th headline


class TestGenerateBulletinConvenience:
    """Tests for generate_bulletin() convenience function."""

    def test_generate_bulletin_success(self):
        """generate_bulletin should return BulletinScript on success."""
        weather = WeatherData(
            temperature=70,
            conditions="Clear",
            forecast_short="Nice day ahead.",
            timestamp=datetime.now(),
        )

        mock_bulletin = BulletinScript(
            script_text="Test bulletin",
            word_count=2,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        with patch("ai_radio.script_writer.ClaudeScriptWriter") as mock_writer_class:
            mock_writer = Mock()
            mock_writer.generate_bulletin.return_value = mock_bulletin
            mock_writer_class.return_value = mock_writer

            result = generate_bulletin(weather=weather)

            assert result == mock_bulletin

    def test_generate_bulletin_initialization_failure(self):
        """generate_bulletin should return None if writer initialization fails."""
        with patch("ai_radio.script_writer.ClaudeScriptWriter") as mock_writer_class:
            mock_writer_class.side_effect = ValueError("No API key")

            result = generate_bulletin()

            assert result is None
