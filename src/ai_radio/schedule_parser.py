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
        self.client = genai.Client(api_key=config.api_keys.gemini_api_key)

    def parse(self, user_input: str) -> ParsedSchedule:
        """Parse natural language to structured schedule.

        Args:
            user_input: Natural language schedule description

        Returns:
            ParsedSchedule with structured data
        """
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
