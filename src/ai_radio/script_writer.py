"""Radio bulletin script generation using Claude LLM.

Generates natural, conversational radio bulletin scripts from weather and news data.
Uses Anthropic Claude API with structured prompts for consistent output.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from anthropic import Anthropic, APIError

from .config import config
from .news import NewsData
from .weather import WeatherData

logger = logging.getLogger(__name__)


@dataclass
class BulletinScript:
    """Generated radio bulletin script with metadata."""

    script_text: str  # Complete bulletin script for TTS
    word_count: int
    timestamp: datetime
    includes_weather: bool
    includes_news: bool


class ClaudeScriptWriter:
    """Claude-powered radio bulletin script generator.

    Generates natural, conversational scripts from weather and news data.
    Designed for 60-90 second radio segments.
    """

    SYSTEM_PROMPT = """You are a professional radio host writing a brief news and weather bulletin for a community radio station.

Guidelines:
- Write in a natural, conversational tone (like you're talking to a friend)
- Keep it concise: 60-90 seconds when read aloud (150-225 words)
- Start with a friendly greeting and station identification
- Present weather first, then 2-3 top news headlines
- Use clear, simple language - avoid jargon
- End with a warm sign-off
- DO NOT include any stage directions, sound effects, or formatting
- Output ONLY the script text that will be spoken"""

    def __init__(self):
        """Initialize Claude client with API key from config."""
        self.api_key = config.llm_api_key
        if not self.api_key:
            raise ValueError("RADIO_LLM_API_KEY not configured")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 512

    def generate_bulletin(
        self,
        weather: Optional[WeatherData] = None,
        news: Optional[NewsData] = None,
    ) -> Optional[BulletinScript]:
        """Generate radio bulletin script from weather and news data.

        Args:
            weather: Current weather conditions and forecast
            news: Recent news headlines from RSS feeds

        Returns:
            BulletinScript with generated text, or None if generation fails
        """
        if not weather and not news:
            logger.error("Cannot generate bulletin: no weather or news data provided")
            return None

        try:
            # Build user prompt with context
            user_prompt = self._build_user_prompt(weather, news)

            logger.info("Generating bulletin script with Claude API")

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract script text
            script_text = response.content[0].text.strip()
            word_count = len(script_text.split())

            logger.info(f"Generated bulletin script: {word_count} words")

            return BulletinScript(
                script_text=script_text,
                word_count=word_count,
                timestamp=datetime.now(),
                includes_weather=weather is not None,
                includes_news=news is not None,
            )

        except APIError as e:
            logger.error(f"Claude API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Bulletin generation failed: {e}")
            return None

    def _build_user_prompt(
        self,
        weather: Optional[WeatherData],
        news: Optional[NewsData],
    ) -> str:
        """Build user prompt with weather and news context.

        Args:
            weather: Weather data to include
            news: News data to include

        Returns:
            Formatted prompt string
        """
        prompt_parts = ["Write a radio news and weather bulletin with this information:\n"]

        # Add weather section
        if weather:
            prompt_parts.append("\n**WEATHER:**")
            prompt_parts.append(f"- Current: {weather.temperature}°F, {weather.conditions}")
            prompt_parts.append(f"- Forecast: {weather.forecast_short}")

        # Add news section
        if news:
            prompt_parts.append("\n**NEWS HEADLINES:**")
            # Limit to top 3 headlines for bulletin brevity
            for i, headline in enumerate(news.headlines[:3], 1):
                prompt_parts.append(f"{i}. {headline.title} (Source: {headline.source})")

        prompt_parts.append(
            "\nGenerate a complete bulletin script that incorporates this information naturally."
        )

        return "\n".join(prompt_parts)


def generate_bulletin(
    weather: Optional[WeatherData] = None,
    news: Optional[NewsData] = None,
) -> Optional[BulletinScript]:
    """Convenience function to generate radio bulletin.

    Args:
        weather: Weather data
        news: News data

    Returns:
        BulletinScript or None if generation fails
    """
    try:
        writer = ClaudeScriptWriter()
        return writer.generate_bulletin(weather, news)
    except ValueError as e:
        logger.error(f"Script writer initialization failed: {e}")
        return None
