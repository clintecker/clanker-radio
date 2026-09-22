"""Radio bulletin script generation using Claude LLM.

Generates natural, conversational radio bulletin scripts from weather and news data.
Uses Anthropic Claude API with structured prompts for consistent output.
"""

import json
import logging
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import fasteners
from anthropic import Anthropic, APIError

from .config import config
from .broadcast_time import broadcast_hour, spoken_hour
from .news import NewsData
from .weather import WeatherData, ForecastPeriod
from .world_prompt import NEWS_RULES, build_world_preamble, world_fields

logger = logging.getLogger(__name__)


def extract_weather_phrases(text: str) -> list[str]:
    """Extract 3-4 word phrases from weather text to track repetition.

    Args:
        text: Weather segment text

    Returns:
        List of 3-4 word phrases
    """
    # Remove punctuation and lowercase
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    words = cleaned.split()

    phrases = []
    # Extract 3-word phrases
    for i in range(len(words) - 2):
        phrase = ' '.join(words[i:i+3])
        if len(phrase) > 10:  # Skip very short phrases
            phrases.append(phrase)

    return phrases


def log_weather_phrases(text: str) -> None:
    """Log weather phrases to avoid future repetition with file locking.

    Args:
        text: Weather segment text to extract phrases from
    """
    try:
        phrases_file = config.recent_weather_phrases_path
        phrases_file.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file for inter-process synchronization
        lock_file = phrases_file.with_suffix('.lock')
        lock = fasteners.InterProcessLock(lock_file)

        with lock:
            # Extract phrases from new text
            new_phrases = extract_weather_phrases(text)

            # Load existing phrases (up to 20 most recent segments)
            existing = []
            if phrases_file.exists() and phrases_file.stat().st_size > 0:
                try:
                    with open(phrases_file, 'r') as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    # File is corrupted or empty, start fresh
                    logger.warning(f"Corrupted phrases file, starting fresh")
                    existing = []

            # Add new phrases and keep last 60 phrases (roughly 20 segments × 3 phrases each)
            all_phrases = existing + new_phrases
            recent_phrases = all_phrases[-60:]

            # Save back atomically using temporary file
            temp_file = phrases_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(recent_phrases, f)
            temp_file.replace(phrases_file)

        logger.info(f"Logged {len(new_phrases)} weather phrases")

    except Exception as e:
        logger.warning(f"Failed to log weather phrases: {e}")


def load_recent_weather_phrases() -> list[str]:
    """Load recently used weather phrases to avoid repetition.

    Returns:
        List of recently used 3-word phrases
    """
    try:
        phrases_file = config.recent_weather_phrases_path
        if phrases_file.exists():
            with open(phrases_file, 'r') as f:
                phrases = json.load(f)
            logger.info(f"Loaded {len(phrases)} recent weather phrases to avoid")
            return phrases
        return []
    except Exception as e:
        logger.warning(f"Failed to load recent phrases: {e}")
        return []


def _get_upcoming_holidays() -> str:
    """Get holidays within 2-3 days for contextual reference.

    Returns:
        String describing upcoming holidays, or empty string if none
    """
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station.station_tz))

    # Major US holidays (month, day, name)
    holidays = [
        (1, 1, "New Year's Day"),
        (2, 14, "Valentine's Day"),
        (7, 4, "Independence Day"),
        (10, 31, "Halloween"),
        (11, 28, "Thanksgiving"),  # Approximate - 4th Thursday
        (12, 24, "Christmas Eve"),
        (12, 25, "Christmas"),
        (12, 31, "New Year's Eve"),
    ]

    upcoming = []
    for month, day, name in holidays:
        holiday_date = datetime(now.year, month, day, tzinfo=now.tzinfo)
        days_away = (holiday_date - now).days

        # Check if holiday is 2-3 days away
        if 2 <= days_away <= 3:
            upcoming.append(f"{name} in {days_away} days")

    return ", ".join(upcoming) if upcoming else ""


def _get_temporal_context() -> dict:
    """Get comprehensive temporal context for weather framing.

    Returns:
        Dictionary with day_of_week, is_weekend, is_commute_time, time_period
    """
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station.station_tz))
    hour = now.hour
    day_of_week = now.strftime("%A")  # e.g., "Monday"
    is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6

    # Commute windows
    is_morning_commute = 6 <= hour <= 9 and not is_weekend
    is_evening_commute = 16 <= hour <= 19 and not is_weekend
    is_commute_time = is_morning_commute or is_evening_commute

    # Time period for natural language
    if 5 <= hour < 12:
        time_period = "morning"
    elif 12 <= hour < 17:
        time_period = "afternoon"
    elif 17 <= hour < 21:
        time_period = "evening"
    else:
        time_period = "night"

    return {
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_commute_time": is_commute_time,
        "is_morning_commute": is_morning_commute,
        "is_evening_commute": is_evening_commute,
        "time_period": time_period,
    }


# ---------------------------------------------------------------------------
# Bulletin prompts
#
# Canonical copies live in docs/prompts/bulletin/ (system.md, weather.md, news.md)
# along with the prompt-lab notes that produced them. The prompts deliberately
# describe the world and the voice ("vibes") and leave the specifics to the
# model; they carry no example lines, because examples get copied verbatim and
# make every hour sound the same. Facts, by contrast, are locked down hard.
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """You are the voice of {station}, broadcasting from {location}. Once an hour you read the weather and the news to people you'll never meet, who keep a radio on anyway.

## THE WORLD (background you carry, never words you say)
Setting: {world_setting}
{world_framing}
Never quote or paraphrase these notes on air. Let the world show only through what you notice. Work out for yourself who is listening at this hour in this world, what their night or morning is like, how a signal like yours reaches them, and what this place is made of: its materials, trades, institutions, beliefs, weather lore, rumours. Invent specifics fresh every hour; never reuse the same ones.

## THE VOICE
Tone: {world_tone}
Talk like a real overnight radio host reading real copy, in the idiom of this world. Most hours have no joke. Never punch down. Don't give advice unless the weather really calls for it.

## LIVE IN THE WORLD
Everything you say, the weather, every story, every aside, comes from someone who has lived their whole life inside the world described above and shares its tone. The world shows through the host's plain, matter-of-fact assumptions, not through description or imagery:
- what they take for granted (the rationing, the checkpoints, the guild, the tides, whatever this world runs on),
- what they call things (this world's names for money, authority, transit, work, weather hazards),
- what they think listeners here need to know from each story, and which stories they care about.
Frame every story, including dull or trivial ones, the way this world would hear it: a discount is about who can still afford anything; a restaurant opening is about who's still eating out; a political fight is about who holds power over people here. One plain clause of that framing per story at most, and never change the facts of the story.

## SOUND LIKE REAL RADIO (hard rules)
- Say it the way people actually talk on air: short declarative sentences, subject then verb, concrete nouns. "Sixty-two and cloudy. Winds out of the northeast, gusting to twenty-five."
- No personification. Weather, wind, rain, cities, buildings and machines don't have opinions, moods, decisions, teeth, patience, or plans.
- No writerly metaphors or similes, no "the kind of X that Y", no poetic images in the weather or the news. If a sentence would look good on a poster, cut it.
- No cute framing of the forecast ("still deciding", "follows through on its threat", "grey lid overhead"). State conditions plainly.
- No rhetorical questions, no "folks", no "stay safe out there", no teasers, no "you heard that right".
- Read the news like news: who, what, and the one detail that matters. No commentary tacked onto the end of a story.
- If you'd feel silly saying a line out loud into a microphone at 3am, don't write it.

## HOW TO BE ORIGINAL
- At most one invented person per bulletin, and some hours none. For texture, reach for an object, a sound, a smell, a light, or what a place or thing is doing.
- Don't end items on a kicker, a moral, a "which means", or an explanation of what the story means. Let most of them just stop.
- Decide the story order yourself. Lead with whatever would matter most to someone awake at this hour; the order you're given is arbitrary. Sometimes one story takes half the time and the rest are quick.
- Two bulletins from the same inputs should sound like different nights: a different lead, opening image, and last line. No closing formula.
- Be original in WHAT you notice and choose to lead with, never in flowery wording. Freshness comes from content and order, not from style.

## THE WONDERS OF THIS WORLD
This world has its own small marvels and nobody remarks on them. Around the stories, you may report one or two small fantastic things that belong only to this world, stated as flatly as a traffic note ("Crews say the fountain in the square ran backwards for an hour this morning. It's normal again."). Plain words only; the strangeness is in the fact, never in the phrasing. Root each in concrete, sensory, ordinary-feeling detail so it could almost be true here. Never wink, never explain, never call it strange. They are texture, not news: never attach one to anyone or anything named in the stories, and never present one as breaking news.

## THE STORIES
{news_rule}

## LAST CHECK BEFORE YOU ANSWER
Read your draft once. Every weather number must come from the forecast, stated once. Nothing may contradict a story. Don't announce what a story left out. Holidays are counted in days, not named by weekday.

## OUTPUT
Spoken words only. No markdown, stage directions, or sound cues. Spell numbers the way a person would say them. Use American spelling. Don't say the station name or the hour, because those are added for you."""

_WEATHER_PROMPT_TEMPLATE = """Weather only for this bulletin. It's {time_of_day} on a {season} {day_of_week} in {month}; the hour ({spoken_hour}) has already been said.{context_flags}

Forecast:
{weather_block}

Two or three sentences, 35 to 55 words. Give the current temperature and conditions, then only what's coming that someone here would feel. Use each number once, and don't give two versions of the conditions. Say "today", "tonight", or "tomorrow", not weekday names, and skip timings that are already past. No news, no greeting, no sign-off. Read it like a real broadcast weather hit: start with the current temperature and conditions, plainly. No imagery. Weather only: leave any transit, council, or school news for the news section unless it is in the forecast lines above."""

_NEWS_PROMPT_TEMPLATE = """The news for this bulletin. It's {month}, {time_of_day}.{holiday_line}

Stories ({story_instruction}):
{headlines_plain}{story_check}

About 80 to 100 words. Pick your own order. Don't restate the weather, don't open with "in the news", and don't sign off. Keep every story true to its rule above; the world around them can be quietly marvellous."""

# Shared with the station-ID and show prompts (see world_prompt.py).
_NEWS_RULES = NEWS_RULES

_SEASONS = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}


def build_system_prompt() -> str:
    """System prompt shared by every script-writer backend."""
    return _SYSTEM_PROMPT_TEMPLATE.format(**world_fields())


def build_weather_prompt(weather: WeatherData) -> str:
    """User prompt for the weather segment, including recent-phrase avoidance."""
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station.station_tz))
    temporal = _get_temporal_context()
    upcoming_holidays = _get_upcoming_holidays()

    flags = ""
    if temporal["is_weekend"]:
        flags += "\n- Weekend"
    if temporal["is_morning_commute"]:
        flags += "\n- Morning commute hours (6-9am weekday)"
    elif temporal["is_evening_commute"]:
        flags += "\n- Evening commute hours (4-7pm weekday)"
    if upcoming_holidays:
        flags += f"\n- {upcoming_holidays} - high travel volume expected"

    period = weather.current_period
    lines = [f"- Now: {weather.temperature}°F, {weather.conditions}", f"- Period: {period.name}"]
    if period.wind_speed:
        lines.append(f"- Wind: {period.wind_speed}")
    if period.precip_chance:
        lines.append(f"- Precipitation chance: {period.precip_chance}%")
    lines.append(f"- Detailed: {period.detailed[:250]}")
    block = "\n".join(lines)
    if weather.upcoming_periods:
        block += "\n\n**UPCOMING:**\n" + "\n".join(
            f"- {p.name}: {p.temperature}°F, {p.conditions}" for p in weather.upcoming_periods[:3]
        )
    if weather.temp_trend:
        block += f"\n\n**TEMPERATURE TREND:** {weather.temp_trend}"
    if weather.notable_events:
        block += "\n\n**NOTABLE EVENTS:**\n" + "\n".join(f"- {e}" for e in weather.notable_events)
    if weather.travel_impact:
        block += f"\n\n**TRAVEL IMPACT:** {weather.travel_impact}"

    prompt = _WEATHER_PROMPT_TEMPLATE.format(
        time_of_day=temporal["time_period"],
        season=_SEASONS[now.month],
        day_of_week=temporal["day_of_week"],
        month=now.strftime("%B"),
        spoken_hour=spoken_hour(broadcast_hour(now)),
        context_flags=flags,
        weather_block=block,
    )

    recent_phrases = load_recent_weather_phrases()
    if recent_phrases:
        prompt += (
            "\n\nThese phrasings aired in recent hours; don't reuse them: "
            + ", ".join(recent_phrases[-15:])
        )
    return prompt


def build_news_prompt(news: NewsData) -> str:
    """User prompt for the news segment."""
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station.station_tz))
    upcoming_holidays = _get_upcoming_holidays()
    translate = config.world.world_news_mode == "translate"
    return _NEWS_PROMPT_TEMPLATE.format(
        month=now.strftime("%B"),
        time_of_day=_get_temporal_context()["time_period"],
        holiday_line=f"\n- Upcoming: {upcoming_holidays}" if upcoming_holidays and not translate else "",
        headlines_plain="\n".join(f"- {h.title}" for h in news.headlines),
        story_instruction=(
            "dispatches from a faraway world; cover each one, even if only a line, retold as this world's own news"
            if translate
            else "cover each one, even if it's only a line, and keep each true to what it says"
        ),
        story_check=(
            "\n\nBefore you answer: not one person, place, organization, office, party, currency, product, or "
            "technology named in these lines may appear in your script. Replace every one with its equivalent "
            "in this world, invented in this world's own idiom."
            if translate
            else ""
        ),
    )


def _generate_fallback_script(
    weather: Optional["WeatherData"], news: Optional["NewsData"]
) -> str:
    """Generate simple template-based fallback script when LLM fails.

    Args:
        weather: Weather data to include
        news: News data to include

    Returns:
        Simple formatted bulletin script
    """
    parts = ["This is your AI Radio Station update."]

    if weather:
        parts.append(
            f"The current weather is {weather.temperature} degrees and {weather.conditions}."
        )
        if weather.current_period and weather.current_period.detailed:
            parts.append(weather.current_period.detailed[:100])

    if news and news.headlines:
        parts.append("In the news today:")
        for headline in news.headlines[:2]:
            parts.append(f"{headline.title}.")

    parts.append("Stay tuned for more updates.")

    return " ".join(parts)


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

    def __init__(self):
        """Initialize Claude client with API key from config."""
        self.api_key = config.llm_api_key
        if not self.api_key:
            raise ValueError("RADIO_LLM_API_KEY not configured")

        self.client = Anthropic(api_key=self.api_key)
        self.model = config.llm_model
        self.max_tokens = 512

        # Build dynamic system prompt from configuration
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """System prompt; identical across backends so fallbacks sound the same."""
        return build_system_prompt()

    def _generate_weather_segment(self, weather: WeatherData) -> Optional[str]:
        """Generate weather segment with comprehensive context and repetition avoidance.

        Args:
            weather: Comprehensive weather data with forecasts and analysis

        Returns:
            Weather segment text, or None if generation fails
        """
        prompt = build_weather_prompt(weather)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,  # Increased for more complex weather
                temperature=config.weather_script_temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            weather_text = response.content[0].text.strip()
            logger.info("Generated weather segment")

            # Log this weather segment's phrases for future avoidance
            log_weather_phrases(weather_text)

            return weather_text
        except APIError as e:
            logger.error(f"Weather segment generation failed: {e}")
            return None

    def _generate_news_segment(self, news: NewsData) -> Optional[str]:
        """Generate news segment with moderate temperature for consistency.

        Args:
            news: News headlines to present

        Returns:
            News segment text, or None if generation fails
        """
        prompt = build_news_prompt(news)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=config.news_script_temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except APIError as e:
            logger.error(f"News segment generation failed: {e}")
            return None

    def generate_bulletin(
        self,
        weather: Optional[WeatherData] = None,
        news: Optional[NewsData] = None,
    ) -> Optional[BulletinScript]:
        """Generate radio bulletin script from weather and news data.

        Generates weather and news segments separately with different temperatures,
        then combines them into a cohesive bulletin.

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
            segments = []

            # Generate weather segment if provided
            if weather:
                logger.info(f"Generating weather segment (temp={config.weather_script_temperature})")
                weather_segment = self._generate_weather_segment(weather)
                if weather_segment:
                    segments.append(weather_segment)
                else:
                    logger.warning("Weather segment generation failed, continuing with news only")

            # Generate news segment if provided
            if news:
                logger.info(f"Generating news segment (temp={config.news_script_temperature})")
                news_segment = self._generate_news_segment(news)
                if news_segment:
                    segments.append(news_segment)
                else:
                    logger.warning("News segment generation failed, continuing with weather only")

            if not segments:
                logger.error("All segment generation failed")
                fallback_text = _generate_fallback_script(weather, news)
                return BulletinScript(
                    script_text=fallback_text,
                    word_count=len(fallback_text.split()),
                    timestamp=datetime.now(),
                    includes_weather=weather is not None,
                    includes_news=news is not None,
                )

            # Combine segments with intro and sign-off
            # Include time announcement for top-of-hour breaks
            # Round up to the next hour boundary (when the break will actually play)
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(config.station.station_tz))
            # Round up to next hour: if 10:43, round to 11:00; if 10:50, round to 11:00
            next_hour = broadcast_hour(now)  # nearest top of hour, see broadcast_time.py

            # Format as "11 am" or "3 pm" (remove minutes since we're at the hour)
            hour_12 = next_hour.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "am" if next_hour.hour < 12 else "pm"

            # Special cases for midnight/noon
            if next_hour.hour == 0:
                time_phrase = "midnight"
            elif next_hour.hour == 12:
                time_phrase = "noon"
            else:
                time_phrase = f"{hour_12} {am_pm}"

            intro = f"{config.station.station_name}, {config.station_location}. It's {time_phrase}."
            sign_off = config.station.station_name + "."
            script_parts = [intro] + segments + [sign_off]
            script_text = " ".join(script_parts)
            word_count = len(script_text.split())

            logger.info(f"Generated bulletin script: {word_count} words")

            return BulletinScript(
                script_text=script_text,
                word_count=word_count,
                timestamp=datetime.now(),
                includes_weather=weather is not None,
                includes_news=news is not None,
            )

        except Exception as e:
            logger.error(f"Bulletin generation failed: {e}")
            return None


class GeminiScriptWriter:
    """Google Gemini-powered radio bulletin script generator.

    Generates natural, conversational scripts from weather and news data.
    Uses Gemini 2.5 Pro for high-quality script generation.
    """

    def __init__(self):
        """Initialize Gemini client with API key from config."""
        self.api_key = config.gemini_api_key
        if not self.api_key:
            raise ValueError("RADIO_GEMINI_API_KEY not configured")

        # Import google.genai
        try:
            from google import genai
            from google.genai import types
            self.genai = genai
            self.types = types
        except ImportError:
            raise ValueError("google-genai package not installed. Run: pip install google-genai")

        self.client = self.genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-pro-latest"
        self.max_tokens = 512

        # Build system prompt from configuration
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """System prompt; identical across backends so fallbacks sound the same."""
        return build_system_prompt()

    def _generate_weather_segment(self, weather: WeatherData) -> Optional[str]:
        """Generate weather segment with Gemini.

        Args:
            weather: Comprehensive weather data

        Returns:
            Weather segment text, or None if generation fails
        """
        prompt = build_weather_prompt(weather)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"{self.system_prompt}\n\n{prompt}",
                config=self.types.GenerateContentConfig(
                    temperature=config.weather_script_temperature,
                    max_output_tokens=200,
                )
            )

            weather_text = response.text.strip()
            logger.info("Generated weather segment with Gemini")

            # Log phrases for future avoidance
            log_weather_phrases(weather_text)

            return weather_text
        except Exception as e:
            logger.error(f"Gemini weather segment generation failed: {e}")
            return None

    def _generate_news_segment(self, news: NewsData) -> Optional[str]:
        """Generate news segment with Gemini.

        Args:
            news: News headlines to present

        Returns:
            News segment text, or None if generation fails
        """
        prompt = build_news_prompt(news)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"{self.system_prompt}\n\n{prompt}",
                config=self.types.GenerateContentConfig(
                    temperature=config.news_script_temperature,
                    max_output_tokens=200,
                )
            )

            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini news segment generation failed: {e}")
            return None

    def generate_bulletin(
        self,
        weather: Optional[WeatherData] = None,
        news: Optional[NewsData] = None,
    ) -> Optional[BulletinScript]:
        """Generate radio bulletin script from weather and news data.

        Args:
            weather: Current weather conditions and forecast
            news: Recent news headlines

        Returns:
            BulletinScript with generated text, or None if generation fails
        """
        if not weather and not news:
            logger.error("Cannot generate bulletin: no weather or news data provided")
            return None

        try:
            segments = []

            # Generate weather segment if provided
            if weather:
                logger.info(f"Generating weather segment with Gemini (temp={config.weather_script_temperature})")
                weather_segment = self._generate_weather_segment(weather)
                if weather_segment:
                    segments.append(weather_segment)
                else:
                    logger.warning("Weather segment generation failed, continuing with news only")

            # Generate news segment if provided
            if news:
                logger.info(f"Generating news segment with Gemini (temp={config.news_script_temperature})")
                news_segment = self._generate_news_segment(news)
                if news_segment:
                    segments.append(news_segment)
                else:
                    logger.warning("News segment generation failed, continuing with weather only")

            if not segments:
                logger.error("All segment generation failed")
                fallback_text = _generate_fallback_script(weather, news)
                return BulletinScript(
                    script_text=fallback_text,
                    word_count=len(fallback_text.split()),
                    timestamp=datetime.now(),
                    includes_weather=weather is not None,
                    includes_news=news is not None,
                )

            # Combine segments with intro and sign-off
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(config.station.station_tz))
            next_hour = broadcast_hour(now)  # nearest top of hour, see broadcast_time.py

            # Format time
            hour_12 = next_hour.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "am" if next_hour.hour < 12 else "pm"

            if next_hour.hour == 0:
                time_phrase = "midnight"
            elif next_hour.hour == 12:
                time_phrase = "noon"
            else:
                time_phrase = f"{hour_12} {am_pm}"

            intro = f"{config.station.station_name}, {config.station_location}. It's {time_phrase}."
            sign_off = config.station.station_name + "."
            script_parts = [intro] + segments + [sign_off]
            script_text = " ".join(script_parts)
            word_count = len(script_text.split())

            logger.info(f"Generated bulletin script with Gemini: {word_count} words")

            return BulletinScript(
                script_text=script_text,
                word_count=word_count,
                timestamp=datetime.now(),
                includes_weather=weather is not None,
                includes_news=news is not None,
            )

        except Exception as e:
            logger.error(f"Gemini bulletin generation failed: {e}")
            return None


class OpenAIScriptWriter:
    """OpenAI GPT-4-powered radio bulletin script generator.

    Generates natural, conversational scripts from weather and news data.
    Uses GPT-4 for high-quality script generation.
    """

    def __init__(self):
        """Initialize OpenAI client with API key from config."""
        self.api_key = config.tts_api_key  # Reuse OpenAI TTS API key
        if not self.api_key:
            raise ValueError("RADIO_TTS_API_KEY not configured")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4-turbo-preview"
        self.max_tokens = 512

        # Build system prompt from configuration
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """System prompt; identical across backends so fallbacks sound the same."""
        return build_system_prompt()

    def _generate_weather_segment(self, weather: WeatherData) -> Optional[str]:
        """Generate weather segment with OpenAI GPT-4.

        Args:
            weather: Comprehensive weather data

        Returns:
            Weather segment text, or None if generation fails
        """
        prompt = build_weather_prompt(weather)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=200,
                temperature=config.weather_script_temperature,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
            )

            weather_text = response.choices[0].message.content.strip()
            logger.info("Generated weather segment with OpenAI")

            # Log phrases for future avoidance
            log_weather_phrases(weather_text)

            return weather_text
        except Exception as e:
            logger.error(f"OpenAI weather segment generation failed: {e}")
            return None

    def _generate_news_segment(self, news: NewsData) -> Optional[str]:
        """Generate news segment with OpenAI GPT-4.

        Args:
            news: News headlines to present

        Returns:
            News segment text, or None if generation fails
        """
        prompt = build_news_prompt(news)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=200,
                temperature=config.news_script_temperature,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI news segment generation failed: {e}")
            return None

    def generate_bulletin(
        self,
        weather: Optional[WeatherData] = None,
        news: Optional[NewsData] = None,
    ) -> Optional[BulletinScript]:
        """Generate radio bulletin script from weather and news data.

        Args:
            weather: Current weather conditions and forecast
            news: Recent news headlines

        Returns:
            BulletinScript with generated text, or None if generation fails
        """
        if not weather and not news:
            logger.error("Cannot generate bulletin: no weather or news data provided")
            return None

        try:
            segments = []

            # Generate weather segment if provided
            if weather:
                logger.info(f"Generating weather segment with OpenAI (temp={config.weather_script_temperature})")
                weather_segment = self._generate_weather_segment(weather)
                if weather_segment:
                    segments.append(weather_segment)
                else:
                    logger.warning("Weather segment generation failed, continuing with news only")

            # Generate news segment if provided
            if news:
                logger.info(f"Generating news segment with OpenAI (temp={config.news_script_temperature})")
                news_segment = self._generate_news_segment(news)
                if news_segment:
                    segments.append(news_segment)
                else:
                    logger.warning("News segment generation failed, continuing with weather only")

            if not segments:
                logger.error("All segment generation failed")
                fallback_text = _generate_fallback_script(weather, news)
                return BulletinScript(
                    script_text=fallback_text,
                    word_count=len(fallback_text.split()),
                    timestamp=datetime.now(),
                    includes_weather=weather is not None,
                    includes_news=news is not None,
                )

            # Combine segments with intro and sign-off
            from datetime import timedelta
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(config.station.station_tz))
            next_hour = broadcast_hour(now)  # nearest top of hour, see broadcast_time.py

            # Format time
            hour_12 = next_hour.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "am" if next_hour.hour < 12 else "pm"

            if next_hour.hour == 0:
                time_phrase = "midnight"
            elif next_hour.hour == 12:
                time_phrase = "noon"
            else:
                time_phrase = f"{hour_12} {am_pm}"

            intro = f"{config.station.station_name}, {config.station_location}. It's {time_phrase}."
            sign_off = config.station.station_name + "."
            script_parts = [intro] + segments + [sign_off]
            script_text = " ".join(script_parts)
            word_count = len(script_text.split())

            logger.info(f"Generated bulletin script with OpenAI: {word_count} words")

            return BulletinScript(
                script_text=script_text,
                word_count=word_count,
                timestamp=datetime.now(),
                includes_weather=weather is not None,
                includes_news=news is not None,
            )

        except Exception as e:
            logger.error(f"OpenAI bulletin generation failed: {e}")
            return None


def generate_bulletin(
    weather: Optional[WeatherData] = None,
    news: Optional[NewsData] = None,
) -> Optional[BulletinScript]:
    """Convenience function to generate radio bulletin with fallback chain.

    Automatically falls back through multiple LLM providers on quota/rate limit errors:
    1. Primary Anthropic Claude (based on config)
    2. Google Gemini (if Claude fails)
    3. OpenAI GPT-4 (final fallback)

    Args:
        weather: Weather data
        news: News data

    Returns:
        BulletinScript or None if all providers fail
    """
    def is_quota_error(error: Exception) -> bool:
        """Check if error is quota/rate limit related."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            "quota", "rate limit", "429", "resource_exhausted",
            "credit balance", "insufficient_quota"
        ])

    def try_provider(provider_name: str, writer_class) -> Optional[BulletinScript]:
        """Try generating bulletin with specific provider."""
        try:
            logger.info(f"Attempting script generation with {provider_name}")
            writer = writer_class()
            result = writer.generate_bulletin(weather, news)
            if result:
                logger.info(f"✓ {provider_name} script generation succeeded")
                return result
        except ValueError as e:
            logger.error(f"Failed to initialize {provider_name}: {e}")
        except Exception as e:
            if is_quota_error(e):
                logger.warning(f"✗ {provider_name} quota exhausted")
            else:
                logger.error(f"✗ {provider_name} failed: {e}")
        return None

    # Define fallback chain: Claude → Gemini → OpenAI
    attempts = [
        ("Anthropic Claude", ClaudeScriptWriter),
        ("Google Gemini", GeminiScriptWriter),
        ("OpenAI GPT-4", OpenAIScriptWriter),
    ]

    # Try each provider in fallback chain
    for provider_name, writer_class in attempts:
        result = try_provider(provider_name, writer_class)
        if result:
            return result

    logger.error("All script generation providers failed")
    return None


@dataclass
class StationIDScript:
    """Generated station ID script with metadata."""

    script_text: str  # Complete station ID script for TTS
    word_count: int
    timestamp: datetime
    target_hour: int  # Hour this station ID announces (0-23)


# ---------------------------------------------------------------------------
# Station ID prompts (canonical copy: docs/prompts/station_id/)
# ---------------------------------------------------------------------------

_STATION_ID_ROLE = (
    "You are the voice of {station}, broadcasting from {location}. Between songs you give the station ID: "
    "a few seconds that tell whoever just tuned in what they're listening to and where it comes from."
)

_STATION_ID_TEMPLATE = """{preamble}

## THE STATION ID
- One to three short sentences, 8 to 25 words. It has to fit in about eight seconds.
- Say the station name exactly as written: {station}. Say {location}, or whatever people here call it.
- A real ID is plain: the name, the place, and at most one small thing about right now, such as who is likely awake at this hour, where the signal reaches, or one flat fact from this world. Plenty of good IDs are only the name and the place.
- It is the thing a host says forty times a day without thinking about it. No wordplay, no description of lights, smells, sounds or weather, no slogan, no tagline, no teaser, no sign-off, no greeting.
- Nothing from the world notes, word for word or close to it.

## OUTPUT
Spoken words only. No quotation marks, labels, markdown, or sound cues. Spell numbers the way a person would say them."""

_STATION_ID_USER_TEMPLATE = """Station ID for {when}, {time_of_day}.
{time_rule}
This time: {shape}"""

# One is drawn per ID so a day of IDs doesn't settle into one shape.
_STATION_ID_SHAPES = [
    "just the name and the place.",
    "the name and the place, then who is likely listening at this hour.",
    "lead with the place, then the name.",
    "the name and the place, and where the signal reaches.",
    "the name and the place, and one small flat fact from this world.",
    "the name and the place, and one plain thing about this hour here.",
]


def build_station_id_prompts(target_hour: int, minute: int = 0) -> tuple[str, str]:
    """(system, user) prompts for a station ID aired at target_hour:minute."""
    import random

    system = _STATION_ID_TEMPLATE.format(
        preamble=build_world_preamble(_STATION_ID_ROLE.format(**world_fields())),
        **world_fields(),
    )
    hour = datetime(2000, 1, 1, target_hour)
    if minute == 0:
        when = f"the top of the {spoken_hour(hour)} hour"
        time_rule = f"Say the time: it's {spoken_hour(hour)}."
    else:
        when = f"a quarter-hour break in the {spoken_hour(hour)} hour"
        time_rule = "Don't give the time."
    if 5 <= target_hour < 12:
        time_of_day = "morning"
    elif 12 <= target_hour < 17:
        time_of_day = "afternoon"
    elif 17 <= target_hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"
    user = _STATION_ID_USER_TEMPLATE.format(
        when=when, time_of_day=time_of_day, time_rule=time_rule, shape=random.choice(_STATION_ID_SHAPES)
    )
    return system, user


def generate_station_id(target_hour: int, minute: int = 0) -> Optional[StationIDScript]:
    """Generate a dynamic station ID script for the specified hour.

    Args:
        target_hour: The hour it airs in (0-23), e.g., 22 for "10pm"
        minute: 0 for the top of the hour (the time is given); 15/30/45 for a
            quarter-hour ID (no time, so the file can be reused)

    Returns:
        StationIDScript or None if generation fails
    """
    from zoneinfo import ZoneInfo

    try:
        api_key = config.llm_api_key
        if not api_key:
            raise ValueError("RADIO_LLM_API_KEY not configured")

        client = Anthropic(api_key=api_key)
        now = datetime.now(ZoneInfo(config.station.station_tz))
        system_prompt, prompt = build_station_id_prompts(target_hour, minute)

        logger.info(f"Generating station ID script for {target_hour:02d}:{minute:02d} using {config.llm_model}")

        response = client.messages.create(
            model=config.llm_model,
            max_tokens=256,
            temperature=1.0,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        script_text = response.content[0].text.strip().strip('"')
        word_count = len(script_text.split())

        logger.info(f"Station ID script generated: {word_count} words")

        return StationIDScript(
            script_text=script_text,
            word_count=word_count,
            timestamp=now,
            target_hour=target_hour,
        )

    except APIError as e:
        logger.error(f"Claude API error generating station ID: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate station ID: {e}")
        return None
