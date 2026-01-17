"""Natural language schedule parser using Gemini."""
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from google import genai

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ParsedSchedule:
    """Parsed schedule result."""
    name: str
    format: str
    topic_area: str
    days_of_week: List[int]
    start_time: str
    duration_minutes: int
    personas: List[Dict[str, str]]
    content_guidance: str


class ScheduleParser:
    """Parse natural language show schedules."""

    def __init__(self):
        """Initialize the schedule parser.

        Raises:
            ValueError: If RADIO_GEMINI_API_KEY is not configured
        """
        if not config.api_keys.gemini_api_key:
            raise ValueError("RADIO_GEMINI_API_KEY not configured")

        self.client = genai.Client(
            api_key=config.api_keys.gemini_api_key.get_secret_value()
        )

    def parse(self, user_input: str) -> ParsedSchedule:
        """Parse natural language to structured schedule.

        Args:
            user_input: Natural language schedule description

        Returns:
            ParsedSchedule with structured data

        Raises:
            ValueError: If input is empty, too long, JSON is invalid, or required fields are missing
            RuntimeError: If API call or parsing fails
        """
        # Input validation
        if not user_input or not user_input.strip():
            raise ValueError("Cannot parse empty schedule description")

        if len(user_input) > 2000:
            raise ValueError("Schedule description too long (max 2000 characters)")

        prompt = f"""Parse this radio show schedule into structured JSON:

"{user_input}"

Return ONLY valid JSON (no markdown, no explanation) with these exact fields:
{{
    "name": "Generated show name (short, descriptive)",
    "format": "interview" or "two_host_discussion",
    "topic_area": "What the show discusses",
    "days_of_week": [1,2,3,4,5],
    "start_time": "09:00",
    "duration_minutes": 8,
    "personas": [
        {{"name": "Person name", "traits": "personality traits"}},
        {{"name": "Another person", "traits": "personality traits"}}
    ],
    "content_guidance": "Topics/themes extracted from description"
}}

Days: 0=Sunday, 1=Monday, ..., 6=Saturday
Time: 24-hour format like "14:30"
Format: Use "interview" for host+expert, "two_host_discussion" for two hosts debating
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=prompt
            )

            # Extract JSON from response
            text = response.text.strip()
            if text.startswith("```"):
                # Remove markdown code blocks
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            data = json.loads(text.strip())

            # Validate required fields
            required_fields = [
                "name",
                "format",
                "topic_area",
                "days_of_week",
                "start_time",
                "personas"
            ]
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise ValueError(f"Response missing required fields: {missing}")

            return ParsedSchedule(
                name=data["name"],
                format=data["format"],
                topic_area=data["topic_area"],
                days_of_week=data["days_of_week"],
                start_time=data["start_time"],
                duration_minutes=data.get("duration_minutes", 8),
                personas=data["personas"],
                content_guidance=data.get("content_guidance", "")
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
        except ValueError:
            # Re-raise ValueError (from missing fields check or JSONDecodeError)
            raise
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            raise ValueError(f"Incomplete schedule data: {e}")
        except Exception as e:
            logger.exception("Schedule parsing failed")
            raise RuntimeError(f"Failed to parse schedule: {e}")
