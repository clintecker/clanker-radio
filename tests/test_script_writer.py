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

from conftest import create_test_weather_data


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
            mock_config.llm_model = "claude-3-5-sonnet-20241022"

            writer = ClaudeScriptWriter()

            assert writer.api_key == "test-api-key"
            assert writer.model == "claude-3-5-sonnet-20241022"
            assert writer.max_tokens == 512

    def test_generate_bulletin_weather_and_news(self):
        """generate_bulletin should create script from weather and news data."""
        weather = create_test_weather_data(temperature=68, conditions="Sunny")

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

        with patch("ai_radio.script_writer.log_weather_phrases"):
            with patch("ai_radio.script_writer.load_recent_weather_phrases", return_value=[]):
                with patch("ai_radio.script_writer.config") as mock_config:
                    mock_config.llm_api_key = "test-key"
                    mock_config.llm_model = "claude-3-5-sonnet-20241022"
                    mock_config.station_tz = "UTC"
                    mock_config.station_name = "Test Radio"
                    mock_config.station_location = "Test City"
                    mock_config.weather_script_temperature = 0.8
                    mock_config.news_script_temperature = 0.6

                    with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                        mock_client = Mock()
                        mock_anthropic_class.return_value = mock_client

                        # Mock Claude API responses for both weather and news segments
                        weather_response = Mock()
                        weather_content = Mock()
                        weather_content.text = "Currently it's 68 degrees and sunny with clear skies expected."
                        weather_response.content = [weather_content]

                        news_response = Mock()
                        news_content = Mock()
                        news_content.text = "In local news, a local event attracted thousands. The city council approved the budget."
                        news_response.content = [news_content]

                        # Return different responses for weather and news calls
                        mock_client.messages.create.side_effect = [weather_response, news_response]

                        writer = ClaudeScriptWriter()
                        bulletin = writer.generate_bulletin(weather, news)

                        # Verify bulletin
                        assert bulletin is not None
                        assert bulletin.includes_weather is True
                        assert bulletin.includes_news is True
                        assert bulletin.word_count > 0
                        assert isinstance(bulletin.timestamp, datetime)
                        # Check that both segments were combined
                        assert "Test Radio" in bulletin.script_text
                        assert "Test City" in bulletin.script_text

    def test_generate_bulletin_weather_only(self):
        """generate_bulletin should create weather-only bulletin."""
        weather = create_test_weather_data(temperature=72, conditions="Partly Cloudy")

        with patch("ai_radio.script_writer.log_weather_phrases"):
            with patch("ai_radio.script_writer.load_recent_weather_phrases", return_value=[]):
                with patch("ai_radio.script_writer.config") as mock_config:
                    mock_config.llm_api_key = "test-key"
                    mock_config.llm_model = "claude-3-5-sonnet-20241022"
                    mock_config.station_tz = "UTC"
                    mock_config.station_name = "Test Radio"
                    mock_config.station_location = "Test City"
                    mock_config.weather_script_temperature = 0.8
                    mock_config.news_script_temperature = 0.6

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
            mock_config.llm_model = "claude-3-5-sonnet-20241022"
            mock_config.station_tz = "UTC"
            mock_config.station_name = "Test Radio"
            mock_config.station_location = "Test City"
            mock_config.weather_script_temperature = 0.8
            mock_config.news_script_temperature = 0.6

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

    def test_generate_bulletin_api_error_with_fallback(self):
        """generate_bulletin should return fallback script on API error."""
        weather = create_test_weather_data(temperature=60, conditions="Rainy")

        news = NewsData(
            headlines=[
                NewsHeadline(title="Breaking news", source="Test", link="https://example.com/1")
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        with patch("ai_radio.script_writer.log_weather_phrases"):
            with patch("ai_radio.script_writer.load_recent_weather_phrases", return_value=[]):
                with patch("ai_radio.script_writer.config") as mock_config:
                    mock_config.llm_api_key = "test-key"
                    mock_config.llm_model = "claude-3-5-sonnet-20241022"
                    mock_config.station_tz = "UTC"
                    mock_config.station_name = "Test Radio"
                    mock_config.station_location = "Test City"
                    mock_config.weather_script_temperature = 0.8
                    mock_config.news_script_temperature = 0.6

                    with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                        mock_client = Mock()
                        mock_anthropic_class.return_value = mock_client

                        # Simulate API error with proper request mock
                        mock_request = Mock()
                        mock_client.messages.create.side_effect = APIError(
                            "API rate limit", body=None, request=mock_request
                        )

                        writer = ClaudeScriptWriter()
                        bulletin = writer.generate_bulletin(weather=weather, news=news)

                        # Should return fallback script instead of None
                        assert bulletin is not None
                        assert "AI Radio Station update" in bulletin.script_text
                        assert "60 degrees" in bulletin.script_text
                        assert "Rainy" in bulletin.script_text
                        assert "Breaking news" in bulletin.script_text
                        assert bulletin.includes_weather is True
                        assert bulletin.includes_news is True

    def test_generate_bulletin_limits_headlines(self):
        """generate_bulletin should use all headlines in prompt (not limiting)."""
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
            mock_config.llm_model = "claude-3-5-sonnet-20241022"
            mock_config.station_tz = "UTC"
            mock_config.station_name = "Test Radio"
            mock_config.station_location = "Test City"
            mock_config.weather_script_temperature = 0.8
            mock_config.news_script_temperature = 0.6

            with patch("ai_radio.script_writer.Anthropic") as mock_anthropic_class:
                mock_client = Mock()
                mock_anthropic_class.return_value = mock_client

                mock_response = Mock()
                mock_content = Mock()
                mock_content.text = "News bulletin script"
                mock_response.content = [mock_content]
                mock_client.messages.create.return_value = mock_response

                writer = ClaudeScriptWriter()
                bulletin = writer.generate_bulletin(news=news)

                # Verify bulletin was generated
                assert bulletin is not None
                # The code uses all headlines (no limiting anymore)
                call_kwargs = mock_client.messages.create.call_args[1]
                prompt = call_kwargs["messages"][0]["content"]
                assert "Story 0" in prompt
                assert "Story 9" in prompt  # Should include all headlines


class TestGenerateBulletinConvenience:
    """Tests for generate_bulletin() convenience function with fallback chain."""

    def test_generate_bulletin_success(self):
        """generate_bulletin should return BulletinScript on success with Claude."""
        weather = create_test_weather_data(temperature=70, conditions="Clear")

        mock_bulletin = BulletinScript(
            script_text="Test bulletin",
            word_count=2,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        with patch("ai_radio.script_writer.log_weather_phrases"):
            with patch("ai_radio.script_writer.load_recent_weather_phrases", return_value=[]):
                with patch("ai_radio.script_writer.ClaudeScriptWriter") as mock_claude:
                    mock_writer = Mock()
                    mock_writer.generate_bulletin.return_value = mock_bulletin
                    mock_claude.return_value = mock_writer

                    result = generate_bulletin(weather=weather)

                    assert result == mock_bulletin
                    # Claude should be tried first
                    mock_claude.assert_called_once()

    def test_generate_bulletin_fallback_to_gemini(self):
        """generate_bulletin should fallback to Gemini if Claude quota exhausted."""
        weather = create_test_weather_data(temperature=70, conditions="Clear")

        mock_bulletin = BulletinScript(
            script_text="Test bulletin from Gemini",
            word_count=4,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        with patch("ai_radio.script_writer.log_weather_phrases"):
            with patch("ai_radio.script_writer.load_recent_weather_phrases", return_value=[]):
                with patch("ai_radio.script_writer.ClaudeScriptWriter") as mock_claude:
                    with patch("ai_radio.script_writer.GeminiScriptWriter") as mock_gemini:
                        # Claude fails with quota error
                        mock_claude.side_effect = ValueError("credit balance")

                        # Gemini succeeds
                        mock_gemini_writer = Mock()
                        mock_gemini_writer.generate_bulletin.return_value = mock_bulletin
                        mock_gemini.return_value = mock_gemini_writer

                        result = generate_bulletin(weather=weather)

                        assert result == mock_bulletin
                        # Both should be attempted
                        mock_claude.assert_called_once()
                        mock_gemini.assert_called_once()

    def test_generate_bulletin_initialization_failure(self):
        """generate_bulletin should try all providers before returning None."""
        with patch("ai_radio.script_writer.ClaudeScriptWriter") as mock_claude:
            with patch("ai_radio.script_writer.GeminiScriptWriter") as mock_gemini:
                with patch("ai_radio.script_writer.OpenAIScriptWriter") as mock_openai:
                    # All providers fail initialization
                    mock_claude.side_effect = ValueError("No Claude API key")
                    mock_gemini.side_effect = ValueError("No Gemini API key")
                    mock_openai.side_effect = ValueError("No OpenAI API key")

                    result = generate_bulletin()

                    assert result is None
                    # All three should be attempted
                    mock_claude.assert_called_once()
                    mock_gemini.assert_called_once()
                    mock_openai.assert_called_once()
