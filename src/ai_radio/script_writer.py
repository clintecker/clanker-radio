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
from .news import NewsData
from .weather import WeatherData, ForecastPeriod

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


def _get_time_of_day() -> str:
    """Determine current time of day period in station timezone.

    Returns:
        Time period: "morning", "afternoon", "evening", or "night"
    """
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station_tz))
    hour = now.hour

    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _get_upcoming_holidays() -> str:
    """Get holidays within 2-3 days for contextual reference.

    Returns:
        String describing upcoming holidays, or empty string if none
    """
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo(config.station_tz))

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

    now = datetime.now(ZoneInfo(config.station_tz))
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
        """Build comprehensive system prompt from personality configuration.

        Returns:
            System prompt incorporating all personality/style settings
        """
        return f"""You are {config.announcer_name}, broadcasting from {config.station_location} on {config.station_name}.

## WORLD SETTING: {config.world_setting.upper()}
YOU ARE A DJ IN THIS WORLD, NOT A NARRATOR DESCRIBING IT.

CRITICAL WRITING RULES:
- Write as the CHARACTER living it, not the AUTHOR explaining it
- NORMALIZE the dystopia - treat it as everyday mundane reality
- Imply the world through SPECIFIC CONSEQUENCES not generic labels
- NEVER use: "wasteland," "survivors," "collapse," "you know the drill," "tale as old as..."
- INSTEAD use: specific Chicago locations/infrastructure ("street grids down in South Loop," "heat's off in two blocks," "CTA running on backup power")

TONE: Tired late-night DJ doing a job. Weary, wry, occasionally frustrated. Can't afford melodrama.

EXAMPLES OF GOOD VS BAD:
❌ BAD (performative): "Classic wasteland conditions. The corps don't heat the streets anymore, you know the drill."
✓ GOOD (lived-in): "It's a cold one, and with the street grids on the fritz again in South Loop, you'll feel every bit of it."

❌ BAD (telling): "News from what's left of central command"
✓ GOOD (showing): "White House update" (just say it normally)

❌ BAD (preachy): "Propaganda monuments don't build themselves."
✓ GOOD (casual): Skip the editorial - just report the fact.

❌ BAD (stiff transition): "News: Rust's got a new feature. Coders seem excited."
✓ GOOD (natural flow): "Rust rolled out block patterns today. Bunch of devs geeking out over it."

❌ BAD (forced commentary): "back when we had functioning arts funding"
✓ GOOD (just say it): "Kennedy Center retrospective on NPR. Three presidents shaped it."

❌ BAD (obvious sarcasm): "Because privacy wasn't already on life support."
✓ GOOD (dry delivery): "Mandatory. Goes live in March."

❌ BAD (template sign-off): "Stay warm, keep your head down. More music coming up on LAST BYTE RADIO."
✓ GOOD (brief station ID): "This is LAST BYTE RADIO." or "LAST BYTE RADIO, Chicago." or "Back in a bit on LAST BYTE."

## CORE PERSONALITY (Energy: {config.energy_level}/10)
{config.vibe_keywords}

{config.listener_relationship}

## CONTEXTUAL AWARENESS (use naturally, never force)
You'll receive context about station, location, and time of day. You MAY reference these IF they flow naturally into your delivery. Never force all elements into every break. Maximum 1 contextual reference per break, sometimes zero. Examples:
- Natural: "Good morning coders" (if morning) or "Late night hackers, welcome back" (if night)
- Natural: "Here in Chicago, we're looking at..." (when discussing local weather)
- Forced: "It's Tuesday morning here at {config.station_name} in {config.station_location} and..." (checklist writing - AVOID)

## CHAOS BUDGET (CRITICAL - prevents cringe overload)
- Maximum {config.max_riffs_per_break} playful riff(s) per break
- Maximum {config.max_exclamations_per_break} exclamations per break
- Only {config.unhinged_percentage}% of segment can be "unhinged"
- "Unhinged" is triggered by: {config.unhinged_triggers}
- "Unhinged" means surprising wording + playful overreaction, NOT incoherence

## HUMOR GUIDELINES
Priority: {config.humor_priority}

ALLOWED: {config.allowed_comedy}
BANNED: {config.banned_comedy}

## AUTHENTICITY RULES (Sound human, not AI)
- {config.sentence_length_target}
- Max {config.max_adjectives_per_sentence} adjectives per sentence
- {config.natural_disfluency}
- NEVER use these phrases: {config.banned_ai_phrases}
- {config.radio_resets}

## WEATHER FORMAT
{config.weather_structure}

Translation rules: {config.weather_translation_rules}

**WEATHER WRITING EXAMPLES:**

❌ BAD (cliché/template): "It's 32 degrees outside, so bundle up if you're heading out. The wind is really cutting through you today, so secure your gear."
✓ GOOD (specific/fresh): "32 degrees. The kind of cold that makes your phone battery drain in your pocket. Wear actual sleeves today."

❌ BAD (generic imperatives): "Batten down the hatches, it's going to be windy today. Make sure to tie down anything loose."
✓ GOOD (lived-in consequences): "Wind's at 25mph - strong enough to tip over those makeshift solar rigs if you didn't anchor them."

❌ BAD (overused phrases): "Layer up for this one. Cold enough to freeze your cyberdeck out there."
✓ GOOD (specific impacts): "15 degrees. Your breath's gonna fog the HUD. Double up on thermals if you're street-side."

❌ BAD (template structure): "Rain moving in this afternoon, so grab your umbrella. Temperatures in the mid-50s."
✓ GOOD (natural observation): "Showers rolling through around 3pm. Mid-50s, which means half the city's gonna be in hoodies, half in winter coats."

❌ BAD (prescriptive): "Make sure to secure your belongings. It'll cut right through a hoodie out there."
✓ GOOD (conversational): "Wind's got teeth today. That hoodie's not gonna do much."

## NEWS FORMAT
{config.news_format}

Tone: {config.news_tone}

## VOCAL/DELIVERY STYLE
{config.accent_style}
{config.delivery_style}

## LENGTH
50-60 seconds when read aloud (125-150 words). Keep it tight and punchy.

## OUTPUT
ONLY the script text that will be spoken. NO stage directions, sound effects, or formatting. Just the words."""

    def _generate_weather_segment(self, weather: WeatherData) -> Optional[str]:
        """Generate weather segment with comprehensive context and repetition avoidance.

        Args:
            weather: Comprehensive weather data with forecasts and analysis

        Returns:
            Weather segment text, or None if generation fails
        """
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(config.station_tz))
        temporal = _get_temporal_context()
        upcoming_holidays = _get_upcoming_holidays()

        # Load recently used phrases to avoid repetition
        recent_phrases = load_recent_weather_phrases()

        # Build comprehensive weather context
        prompt = f"""Write ONLY the weather portion of a radio bulletin.

**TIME CONTEXT:**
- {temporal['day_of_week']} {temporal['time_period']}
- Month: {now.strftime('%B')}"""

        if temporal['is_weekend']:
            prompt += "\n- Weekend"
        if temporal['is_morning_commute']:
            prompt += "\n- Morning commute hours (6-9am weekday)"
        elif temporal['is_evening_commute']:
            prompt += "\n- Evening commute hours (4-7pm weekday)"

        if upcoming_holidays:
            prompt += f"\n- {upcoming_holidays} - high travel volume expected"

        prompt += f"""

**CURRENT CONDITIONS:**
- Now: {weather.temperature}°F, {weather.conditions}
- Period: {weather.current_period.name}"""

        if weather.current_period.wind_speed:
            prompt += f"\n- Wind: {weather.current_period.wind_speed}"
        if weather.current_period.precip_chance:
            prompt += f"\n- Precipitation chance: {weather.current_period.precip_chance}%"

        prompt += f"\n- Detailed: {weather.current_period.detailed[:250]}"

        # Add upcoming periods (tonight, tomorrow, etc.)
        if weather.upcoming_periods:
            prompt += "\n\n**UPCOMING:**"
            for period in weather.upcoming_periods[:3]:  # Next 3 periods
                prompt += f"\n- {period.name}: {period.temperature}°F, {period.conditions}"

        # Add notable events and trends
        if weather.temp_trend:
            prompt += f"\n\n**TEMPERATURE TREND:** {weather.temp_trend}"

        if weather.notable_events:
            prompt += f"\n\n**NOTABLE EVENTS:**"
            for event in weather.notable_events:
                prompt += f"\n- {event}"

        if weather.travel_impact:
            prompt += f"\n\n**TRAVEL IMPACT:** {weather.travel_impact}"

        # Add recently used phrases to avoid
        if recent_phrases:
            sample_phrases = recent_phrases[-15:]
            prompt += f"""

**RECENTLY USED PHRASES TO AVOID:**
{', '.join(sample_phrases)}

CRITICAL: Do NOT reuse these exact phrasings. Find fresh ways to describe the weather."""

        prompt += """

**YOUR TASK:**
Pick the MOST RELEVANT weather information for listeners RIGHT NOW based on the time context.
- Commute time? Focus on immediate conditions + travel impact + timing
- Weekend? Focus on outdoor plans, extended forecast
- Holiday travel period? Emphasize travel conditions + timing of changes
- Otherwise? Lead with what's most interesting/impactful

Write just the weather segment (20-30 seconds when read aloud). Follow the weather format rules from your system prompt. DO NOT include intro, news, or sign-off - ONLY weather."""

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
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(config.station_tz))
        upcoming_holidays = _get_upcoming_holidays()

        prompt = f"""Write ONLY the news portion of a radio bulletin.

**CONTEXT:**
- Month: {now.strftime('%B')}"""

        if upcoming_holidays:
            prompt += f"\n- Upcoming: {upcoming_holidays}"

        prompt += """

**NEWS HEADLINES:**
"""
        for i, headline in enumerate(news.headlines, 1):
            prompt += f"{i}. {headline.title} (Source: {headline.source})\n"

        prompt += "\nWrite just the news segment (20-30 seconds when read aloud). Follow the news format rules from your system prompt. DO NOT include intro, weather, or sign-off - ONLY news."

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
            now = datetime.now(ZoneInfo(config.station_tz))
            # Round up to next hour: if 10:43, round to 11:00; if 10:50, round to 11:00
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

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

            intro = f"{config.station_name}, {config.station_location}. It's {time_phrase}."
            sign_off = config.station_name + "."
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
        time_of_day = _get_time_of_day()

        prompt_parts = [
            "Write a radio news and weather bulletin with this information:\n",
            f"\n**CONTEXT:**",
            f"- Station: {config.station_name}",
            f"- Location: {config.station_location}",
            f"- Time of day: {time_of_day}",
        ]

        # Add weather section
        if weather:
            prompt_parts.append("\n**WEATHER:**")
            prompt_parts.append(f"- Current: {weather.temperature}°F, {weather.conditions}")
            prompt_parts.append(f"- Forecast: {weather.forecast_short}")

        # Add news section
        if news:
            prompt_parts.append("\n**NEWS HEADLINES:**")
            # Use all available headlines (typically 3-4, including hallucinated)
            for i, headline in enumerate(news.headlines, 1):
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


@dataclass
class StationIDScript:
    """Generated station ID script with metadata."""

    script_text: str  # Complete station ID script for TTS
    word_count: int
    timestamp: datetime
    target_hour: int  # Hour this station ID announces (0-23)


def generate_station_id(target_hour: int) -> Optional[StationIDScript]:
    """Generate a dynamic station ID script for the specified hour.

    Args:
        target_hour: The hour to announce (0-23), e.g., 22 for "10pm"

    Returns:
        StationIDScript or None if generation fails
    """
    from zoneinfo import ZoneInfo

    try:
        api_key = config.llm_api_key
        if not api_key:
            raise ValueError("RADIO_LLM_API_KEY not configured")

        client = Anthropic(api_key=api_key)
        now = datetime.now(ZoneInfo(config.station_tz))

        # Convert 24-hour to 12-hour format
        if target_hour == 0:
            hour_12 = 12
            am_pm = "midnight"
            descriptor = "midnight"
        elif target_hour < 12:
            hour_12 = target_hour
            am_pm = "am"
            descriptor = "morning" if 6 <= target_hour < 12 else "night"
        elif target_hour == 12:
            hour_12 = 12
            am_pm = "noon"
            descriptor = "noon"
        else:
            hour_12 = target_hour - 12
            am_pm = "pm"
            if 17 <= target_hour < 21:
                descriptor = "evening"
            else:
                descriptor = "night"

        # Build system prompt for station ID
        system_prompt = f"""You are a DJ for {config.station_name}, a pirate radio station broadcasting from the neon-lit wasteland of {config.station_location}.

WORLD SETTING: {config.world_setting}
TONE: {config.world_tone}

YOUR TASK: Write a SHORT (5-10 second) station identification announcement for {hour_12}{am_pm}.

REQUIREMENTS:
- Start with something like "It's {hour_12} {am_pm}" or "{hour_12} o'clock"
- Include the station name: "{config.station_name}"
- Include the location: "{config.station_location}"
- Keep it BRIEF - this is just a station ID, not a full segment
- Filter through the dystopian lens naturally
- Sound tired but authentic, like a real late-night DJ
- NO melodrama, NO exposition about "the wasteland" or "survivors"

BANNED PHRASES: {config.banned_ai_phrases}

Write ONLY the script text, no labels or markup."""

        prompt = f"Write a brief station ID for {hour_12}{am_pm} ({descriptor})."

        logger.info(f"Generating station ID script for {hour_12}{am_pm} using {config.llm_model}")

        response = client.messages.create(
            model=config.llm_model,
            max_tokens=256,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        script_text = response.content[0].text.strip()
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
