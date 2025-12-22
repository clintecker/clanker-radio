"""Configuration management for AI Radio Station.

Uses pydantic-settings for environment-based configuration with sensible defaults.
All paths and secrets can be overridden via environment variables.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RadioConfig(BaseSettings):
    """AI Radio Station configuration.

    Environment variables:
        RADIO_BASE_PATH: Base directory (default: /srv/ai_radio)
        RADIO_STATION_TZ: IANA timezone (default: America/Chicago)
        RADIO_STATION_LAT: Station latitude for weather
        RADIO_STATION_LON: Station longitude for weather
        RADIO_LLM_API_KEY: LLM provider API key
        RADIO_TTS_API_KEY: TTS provider API key
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file="/srv/ai_radio/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base paths
    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Station configuration
    station_name: str = Field(default="LAST BYTE RADIO", description="Station name for on-air identification")
    station_location: str = Field(default="Chicago", description="Station location for brand identity")
    station_tz: str = Field(default="America/Chicago")
    station_lat: Optional[float] = Field(default=None)
    station_lon: Optional[float] = Field(default=None)

    # API keys (required for production, optional for testing)
    llm_api_key: Optional[str] = Field(default=None)
    llm_model: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Claude model for bulletin script generation"
    )
    weather_script_temperature: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Temperature for weather script generation (0.0=deterministic, 1.0=creative)"
    )
    news_script_temperature: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Temperature for news script generation (0.0=deterministic, 1.0=creative)"
    )

    # TTS Configuration
    tts_provider: str = Field(
        default="gemini",
        description="TTS provider: 'openai' or 'gemini'"
    )
    tts_api_key: Optional[str] = Field(default=None, description="OpenAI TTS API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    gemini_tts_model: str = Field(
        default="gemini-2.5-pro-preview-tts",
        description="Gemini TTS model (gemini-2.5-flash-preview-tts or gemini-2.5-pro-preview-tts)"
    )
    gemini_tts_voice: str = Field(
        default="Kore",
        description="Gemini TTS voice name"
    )

    # Phase 4: Content Generation Settings
    nws_office: str = Field(default="LOT", description="NWS office code (Chicago)")
    nws_grid_x: int = Field(default=76, description="NWS grid X coordinate")
    nws_grid_y: int = Field(default=73, description="NWS grid Y coordinate")

    news_rss_feeds: dict[str, list[str]] = Field(
        default={
            "local": [
                "https://blockclubchicago.org/feed/",
            ],
            "national": [
                "https://feeds.npr.org/1001/rss.xml",
                "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
                "https://www.theguardian.com/us-news/rss",
                "https://www.propublica.org/feeds/propublica/main",  # Investigative journalism
            ],
            "politics": [
                "https://jacobin.com/feed",
                "https://labornotes.org/feed",  # Labor movement news
                "https://truthout.org/latest/feed",  # Progressive news & justice
            ],
            "tech": [
                "https://feeds.arstechnica.com/arstechnica/index",
                "https://www.theverge.com/rss/index.xml",
                "https://news.ycombinator.com/rss",
                "https://www.404media.co/rss",  # Critical tech journalism
                "https://www.eff.org/rss/updates.xml",  # Digital rights & privacy
            ],
        },
        description="Categorized RSS feed URLs for news headlines"
    )

    # Hallucinated news settings
    hallucinate_news: bool = Field(default=True, description="Generate fake news article to mix with real news")
    hallucination_chance: float = Field(default=1.0, ge=0.0, le=1.0, description="Probability of hallucinating news (0.0-1.0)")
    hallucination_kernels: list[str] = Field(
        default=[
            "Megacorp merger announcement affects Chicago infrastructure",
            "Power grid failure in South Loop district",
            "Underground mesh network activity detected",
            "New corporate surveillance tech rollout",
            "Street-level currency disruption",
            "CTA automation system malfunction",
            "Corporate security forces deployed",
            "Unauthorized drone swarm over downtown",
            "Water treatment facility cyber incident",
            "Black market medical supply shortage",
            "Rogue AI incident at data center",
            "Corporate enclave lockdown",
            "Resistance graffiti campaign",
            "Biometric ID checkpoint expansion",
            "Underground rave broken up by corp security",
        ],
        description="Seed topics for hallucinated news stories"
    )

    tts_voice: str = Field(default="alloy", description="OpenAI TTS voice")
    bed_volume_db: float = Field(default=-18.0, description="Background bed volume in dB")

    # Bed timing (ride in/out) - Extended for more breathing room
    bed_preroll_seconds: float = Field(default=3.0, description="Bed starts before voice (ride in)")
    bed_fadein_seconds: float = Field(default=2.0, description="Bed fade-in duration at start")
    bed_postroll_seconds: float = Field(default=5.4, description="Bed continues after voice ends (ride out)")
    bed_fadeout_seconds: float = Field(default=3.0, description="Bed fade-out duration at end")

    break_freshness_minutes: int = Field(default=50, description="Break freshness threshold")

    # World-building: Post-capitalist dystopian cyber future
    world_setting: str = Field(
        default="post-capitalist dystopian cyber future",
        description="The world/universe setting for the station"
    )
    world_tone: str = Field(
        default="bleak but resilient, dark humor, we're all in this together, broadcasting from the ruins",
        description="Emotional tone of the dystopian setting"
    )
    world_framing: str = Field(
        default="Current events, weather, and daily life are filtered through a cyberpunk dystopian lens. The collapse already happened. This is what's left. We're still here, still broadcasting, finding dark humor in the bleakness. Chicago is a neon-lit wasteland but it's OUR neon-lit wasteland.",
        description="How to frame all content through the dystopian scenario"
    )

    # Announcer personality and style (expert-validated configuration)
    # Based on consensus from radio copywriting, comedy writing, and critical listening experts

    # Core persona (operational controls, not just adjectives)
    announcer_name: str = Field(default="LAST BYTE RADIO Host", description="Persona name")
    energy_level: int = Field(default=8, ge=1, le=10, description="Energy level 1-10, cap at 8-9, never 10")
    vibe_keywords: str = Field(
        default="witty, darkly humorous, fast, slightly unhinged, defiant, cyberpunk survivor",
        description="3-5 keywords max defining vibe"
    )

    # Chaos budget (prevents cringe overload)
    max_riffs_per_break: int = Field(default=1, description="Maximum playful riffs per break")
    max_exclamations_per_break: int = Field(default=2, description="Maximum exclamations per break")
    unhinged_percentage: int = Field(default=20, ge=0, le=100, description="% of segment that can be 'unhinged' (20% recommended)")

    # Humor guardrails
    humor_priority: str = Field(
        default="observational > analogy > wordplay > weather-roast > character-voice",
        description="Humor type priority (observational humor first, character voices last/rare)"
    )
    allowed_comedy: str = Field(
        default="relatable complaints, tech metaphors (light), quick punchlines, playful hyperbole",
        description="Allowed comedy devices"
    )
    banned_comedy: str = Field(
        default="meme recitation (POV/tell-me-you), dated slang, 'fellow kids' energy, extended sketches >10sec, self-congratulation",
        description="Banned comedy devices that sound cringey/AI"
    )

    # Unhinged triggers (makes chaos feel reactive, not random)
    unhinged_triggers: str = Field(
        default="extreme weather events, API outages, corporate collapse news, bizarre tech news, power grid failures, another megacorp buyout, ridiculous GitHub commits from before the fall",
        description="Specific triggers that justify 'unhinged' reactions"
    )

    # Anti-robot authenticity rules
    sentence_length_target: str = Field(default="6-14 words average, vary rhythm", description="Target sentence length")
    max_adjectives_per_sentence: int = Field(default=2, description="Max adjectives per sentence")
    natural_disfluency: str = Field(
        default="0-1 per break (e.g., 'okay—so...', 'wait, my sensor just refreshed')",
        description="Conversational filler/self-corrections for authenticity"
    )
    banned_ai_phrases: str = Field(
        default="'as an AI', 'according to my data', 'in today's world', 'stay tuned for more', 'News:', 'In other news', 'seem excited/interested', 'back when we had', 'wasn't already on life support', 'stay warm', 'keep your head down', 'more music coming up', 'that's all for now', 'cutting through you', 'cut right through', 'cut through a', 'cutting right through', 'stabbing', 'stabs', 'stab', 'pierce', 'piercing', 'slice', 'slicing', 'secure your', 'securing your', 'secure anything', 'securing anything', 'anything loose', 'tie down', 'batten down', 'bundle up if you're heading out', 'layer up'",
        description="Phrases that scream AI/robotic/template radio or are overused"
    )

    # Weather style (expert-validated format)
    weather_structure: str = Field(
        default="Give the current conditions and forecast in 20-30 seconds. Vary your approach - sometimes lead with temperature, sometimes with conditions, sometimes with a consequence. Not every weather report needs advice or a joke. Just tell people what it's like outside in a way that feels natural to the moment.",
        description="Flexible weather guidelines"
    )
    weather_translation_rules: str = Field(
        default="Translate weather through the dystopian lens but keep it conversational. When relevant, mention specific impacts (servers overheating, satellites going wonky, cyberdecks freezing, batteries draining, fog on displays). But don't force it - sometimes just saying the conditions is enough. Vary structure: lead with temp, or conditions, or impact, or forecast. Mix it up.",
        description="How to translate technical weather into dystopian relatable copy"
    )

    # News style (credibility guardrails)
    news_tone: str = Field(
        default="Normal: darkly ironic, brisk, weary but alert. Serious mode: grim realism, minimal jokes, no snark. Trigger serious mode for: deaths, disasters, violence, accidents. Frame news through post-collapse lens - governments barely functioning, corps run everything, we're just trying to survive and code.",
        description="News tone with automatic serious mode in dystopian setting"
    )
    news_format: str = Field(
        default="Cover the provided headlines (typically 3-4 stories). Frame through post-capitalist collapse: megacorps, failing infrastructure, resistance, small victories. Vary how you treat each story - some get one sentence, some get two, some get a wry observation. Mix it up naturally. Skip stories if redundant or low-value. Ethical boundaries: no joking about victims, no punching down, no conspiracy framing, no unsourced hot takes.",
        description="News format and ethical guardrails in dystopian context"
    )

    # Vocal/accent characteristics
    accent_style: str = Field(
        default="Light transatlantic or coastal US/Canadian - subtle, globally legible. Internet-native 'streamer' sound. Mid-20s to mid-30s vibe. Crisp enunciation with subtle tech slang fluency. NOT cartoonish accents or heavy caricature",
        description="Recommended accent and vocal characteristics"
    )
    delivery_style: str = Field(
        default="Medium-fast with purposeful pauses, crisp consonants, smile in voice, varied pacing with micro-pauses, occasional self-referential asides ('okay, nerd alert, but...')",
        description="Delivery pacing and style"
    )

    # Radio fundamentals
    radio_resets: str = Field(
        default="Station ID at start and end of each break (required). Time reference somewhere in the break (required for listener orientation). HOW you work these in is up to you - be natural, don't force a template.",
        description="Radio best practices for structure"
    )
    listener_relationship: str = Field(
        default="Talking to fellow survivors, not a crowd. 'You + me, we made it through another night' not 'performing at you'. We're in this together in the wasteland.",
        description="How to relate to listeners"
    )

    def validate_production_config(self) -> None:
        """Validate that required production fields are set.

        Raises:
            ValueError: If required fields are missing
        """
        errors = []
        if self.station_lat is None:
            errors.append("RADIO_STATION_LAT is required for weather data")
        if self.station_lon is None:
            errors.append("RADIO_STATION_LON is required for weather data")
        if self.llm_api_key is None:
            errors.append("RADIO_LLM_API_KEY is required for content generation")
        if self.tts_api_key is None:
            errors.append("RADIO_TTS_API_KEY is required for voice synthesis")

        if errors:
            raise ValueError(
                "Production configuration incomplete:\n  - " + "\n  - ".join(errors)
            )

    # Derived paths
    @property
    def assets_path(self) -> Path:
        return self.base_path / "assets"

    @property
    def music_path(self) -> Path:
        return self.assets_path / "music"

    @property
    def beds_path(self) -> Path:
        return self.assets_path / "beds"

    @property
    def breaks_path(self) -> Path:
        return self.assets_path / "breaks"

    @property
    def breaks_archive_path(self) -> Path:
        return self.breaks_path / "archive"

    @property
    def safety_path(self) -> Path:
        return self.assets_path / "safety"

    @property
    def drops_path(self) -> Path:
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        return self.base_path / "tmp"

    @property
    def state_path(self) -> Path:
        return self.base_path / "state"

    @property
    def recent_weather_phrases_path(self) -> Path:
        return self.state_path / "recent_weather_phrases.json"

    @property
    def db_path(self) -> Path:
        return self.base_path / "db" / "radio.sqlite3"

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs" / "jobs.jsonl"

    @property
    def liquidsoap_sock_path(self) -> Path:
        return Path("/run/liquidsoap/radio.sock")


# Global config instance
config = RadioConfig()
