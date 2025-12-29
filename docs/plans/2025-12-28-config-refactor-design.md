# Configuration System Refactor - Design Document

**Date:** 2025-12-28
**Status:** Design Phase
**Related Issue:** #14

## Executive Summary

Decompose the 337-line `config.py` monolith into 9 domain-specific configuration modules while maintaining full backward compatibility. The refactor improves clarity, testability, security, and maintainability through clear separation of concerns.

## Problem Statement

The current configuration system has grown into a monolith with mixed concerns:

- **337 lines** in a single `RadioConfig` class
- **Mixed domains**: paths, API keys, personality settings, audio mixing, content sources
- **No separation** between technical config and creative config
- **Testing difficulties**: Global singleton makes isolated testing hard
- **Security concerns**: Secrets not segregated, no SecretStr protection
- **Maintainability**: Hard to understand what's related to what

### Current Issues

```python
# Everything in one class
class RadioConfig(BaseSettings):
    base_path: Path = ...
    llm_api_key: Optional[str] = ...      # Secret not protected
    announcer_name: str = ...              # 87 lines of personality
    bed_volume_db: float = ...
    nws_office: Optional[str] = ...
    # ... 330+ more lines
```

## Design Goals

1. **Clarity** - Clear domain boundaries, single responsibility per config
2. **Testability** - Easy to create test configs without globals
3. **Security** - Secrets isolated with proper SecretStr handling
4. **Validation** - Load-time validation catches errors early
5. **Maintainability** - Easy to find and modify related settings
6. **Backward Compatibility** - Existing code continues working during migration
7. **Type Safety** - Full type hints throughout

## Proposed Architecture

### Domain Decomposition

Split the monolith into **9 domain-specific configs**:

1. **PathsConfig** - All filesystem paths (~50 lines)
2. **APIKeysConfig** - Secrets with SecretStr protection
3. **StationIdentityConfig** - Station name, location, timezone
4. **AnnouncerPersonalityConfig** - Announcer persona (87 lines)
5. **WorldBuildingConfig** - Setting, tone, framing
6. **ContentSourcesConfig** - NWS weather, RSS feeds, news settings
7. **TTSConfig** - TTS provider, voices, models
8. **AudioMixingConfig** - Bed volumes, timing, fade durations
9. **OperationalConfig** - Runtime behavior, scheduling, process limits

### Package Structure

```
src/ai_radio/config/
├── __init__.py              # Public API, exports config singleton
├── base.py                  # RadioConfig (composition root)
├── paths.py                 # PathsConfig
├── api_keys.py              # APIKeysConfig
├── station_identity.py      # StationIdentityConfig
├── announcer.py             # AnnouncerPersonalityConfig
├── world_building.py        # WorldBuildingConfig
├── content_sources.py       # ContentSourcesConfig
├── tts.py                   # TTSConfig
├── audio_mixing.py          # AudioMixingConfig
└── operational.py           # OperationalConfig
```

## Detailed Design

### 1. PathsConfig - Filesystem Paths

**Responsibility:** All filesystem paths and derived path properties

```python
# config/paths.py
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class PathsConfig(BaseSettings):
    """Filesystem paths configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Derived paths as properties (maintains current API)
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
    def bumpers_path(self) -> Path:
        return self.assets_path / "bumpers"

    @property
    def safety_path(self) -> Path:
        return self.assets_path / "safety"

    @property
    def startup_path(self) -> Path:
        return self.assets_path / "startup.mp3"

    @property
    def drops_path(self) -> Path:
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        return self.base_path / "tmp"

    @property
    def public_path(self) -> Path:
        return self.base_path / "public"

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
```

**Design Decision:** Keep derived paths as `@property` methods rather than moving to a separate PathService. This maintains the current API and makes migration smoother.

### 2. APIKeysConfig - Secrets Management

**Responsibility:** All API keys and secrets with proper protection

```python
# config/api_keys.py
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class APIKeysConfig(BaseSettings):
    """API keys and secrets configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    llm_api_key: Optional[SecretStr] = Field(default=None)
    tts_api_key: Optional[SecretStr] = Field(default=None)
    gemini_api_key: Optional[SecretStr] = Field(default=None)

    def validate_production(self) -> None:
        """Validate required keys for production."""
        errors = []
        if self.llm_api_key is None:
            errors.append("RADIO_LLM_API_KEY is required for content generation")
        if self.tts_api_key is None:
            errors.append("RADIO_TTS_API_KEY is required for voice synthesis")
        if errors:
            raise ValueError(
                "Production configuration incomplete:\n  - " + "\n  - ".join(errors)
            )
```

**Key Changes:**
- Use `SecretStr` instead of `Optional[str]` for all secrets
- Secrets are never logged or exposed in error messages
- Clear production validation method

### 3. StationIdentityConfig - Core Station Info

**Responsibility:** Station name, location, timezone, coordinates

```python
# config/station_identity.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class StationIdentityConfig(BaseSettings):
    """Station identity and location configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    station_name: str = Field(
        default="WKRP Coconut Island",
        description="Station name for on-air identification"
    )
    station_location: str = Field(
        default="Coconut Island",
        description="Station location for brand identity"
    )
    station_tz: str = Field(default="Pacific/Honolulu")
    station_lat: Optional[float] = Field(default=None)
    station_lon: Optional[float] = Field(default=None)

    def validate_production(self) -> None:
        """Validate required fields for production."""
        errors = []
        if self.station_lat is None:
            errors.append("RADIO_STATION_LAT is required for weather data")
        if self.station_lon is None:
            errors.append("RADIO_STATION_LON is required for weather data")
        if errors:
            raise ValueError(
                "Production configuration incomplete:\n  - " + "\n  - ".join(errors)
            )
```

**Design Decision:** Separate from WorldBuildingConfig because station identity is core, immutable branding, while world-building is creative direction that can evolve.

### 4. AnnouncerPersonalityConfig - Character Definition

**Responsibility:** Announcer persona, energy level, humor guardrails, delivery style

```python
# config/announcer.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AnnouncerPersonalityConfig(BaseSettings):
    """Announcer persona and style configuration.

    This is the CHARACTER performing on the station.
    Separate from WorldBuildingConfig (the SETTING).
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    # Core persona
    announcer_name: str = Field(default="DJ Coco", description="Persona name")
    energy_level: int = Field(default=5, ge=1, le=10, description="Energy level 1-10")
    vibe_keywords: str = Field(
        default="laid-back, friendly, warm, easygoing, tropical",
        description="3-5 keywords max defining vibe"
    )

    # Chaos budget (prevents cringe overload)
    max_riffs_per_break: int = Field(default=1)
    max_exclamations_per_break: int = Field(default=2)
    unhinged_percentage: int = Field(default=20, ge=0, le=100)

    # Humor guardrails
    humor_priority: str = Field(
        default="observational > analogy > wordplay > weather-roast > character-voice"
    )
    allowed_comedy: str = Field(
        default="relatable complaints, tech metaphors (light), quick punchlines, playful hyperbole"
    )
    banned_comedy: str = Field(
        default="meme recitation (POV/tell-me-you), dated slang, 'fellow kids' energy, extended sketches >10sec, self-congratulation"
    )

    # Unhinged triggers
    unhinged_triggers: str = Field(
        default="hurricanes, tsunami warnings, volcanic activity, coconut shortages, extreme surf conditions, tourist invasions"
    )

    # Anti-robot authenticity rules
    sentence_length_target: str = Field(default="6-14 words average, vary rhythm")
    max_adjectives_per_sentence: int = Field(default=2)
    natural_disfluency: str = Field(
        default="0-1 per break (e.g., 'okay—so...', 'wait, my sensor just refreshed')"
    )
    banned_ai_phrases: str = Field(
        default="'as an AI', 'according to my data', 'in today's world', 'stay tuned for more', 'News:', 'In other news', 'seem excited/interested', 'back when we had', 'wasn't already on life support', 'stay warm', 'keep your head down', 'more music coming up', 'that's all for now', 'cutting through you', 'cut right through', 'cut through a', 'cutting right through', 'stabbing', 'stabs', 'stab', 'pierce', 'piercing', 'slice', 'slicing', 'secure your', 'securing your', 'secure anything', 'securing anything', 'anything loose', 'tie down', 'batten down', 'bundle up if you're heading out', 'layer up'"
    )

    # Weather style
    weather_structure: str = Field(
        default="Give the current conditions and forecast in 20-30 seconds. Vary your approach - sometimes lead with temperature, sometimes with conditions, sometimes with a consequence. Not every weather report needs advice or a joke. Just tell people what it's like outside in a way that feels natural to the moment."
    )
    weather_translation_rules: str = Field(
        default="Keep it breezy and conversational. When relevant, mention specific impacts (beach conditions, outdoor plans, boat weather, tourist activities). But don't force it - sometimes just saying the conditions is enough. Vary structure: lead with temp, or conditions, or impact, or forecast. Mix it up."
    )

    # News style
    news_tone: str = Field(
        default="Normal: laid-back, friendly, conversational. Serious mode: respectful, minimal jokes, no snark. Trigger serious mode for: deaths, disasters, violence, accidents. Keep it real and relatable."
    )
    news_format: str = Field(
        default="Cover the provided headlines (typically 3-4 stories). Keep it natural and conversational. Vary how you treat each story - some get one sentence, some get two, some get a casual observation. Mix it up naturally. Skip stories if redundant or low-value. Ethical boundaries: no joking about victims, no punching down, no conspiracy framing, no unsourced hot takes."
    )

    # Vocal/accent characteristics
    accent_style: str = Field(
        default="Light transatlantic or coastal US/Canadian - subtle, globally legible. Internet-native 'streamer' sound. Mid-20s to mid-30s vibe. Crisp enunciation with subtle tech slang fluency. NOT cartoonish accents or heavy caricature"
    )
    delivery_style: str = Field(
        default="Medium-fast with purposeful pauses, crisp consonants, smile in voice, varied pacing with micro-pauses, occasional self-referential asides ('okay, nerd alert, but...')"
    )

    # Radio fundamentals
    radio_resets: str = Field(
        default="Station ID at start and end of each break (required). Time reference somewhere in the break (required for listener orientation). HOW you work these in is up to you - be natural, don't force a template."
    )
    listener_relationship: str = Field(
        default="Talking to neighbors and friends, not a crowd. 'We're all here living the island life together' not 'performing at you'. Casual, warm, like chatting at the beach."
    )
```

**Design Rationale:** This is the CHARACTER (87 lines). Separating from WorldBuildingConfig (the SETTING) provides:
- **Modularity**: Multiple announcers can perform in the same world
- **Testability**: Test personality-driven generation independently of world context
- **Prompt Engineering Clarity**: World sets the scene, personality provides the persona

### 5. WorldBuildingConfig - Setting Definition

**Responsibility:** Narrative universe, context, tone

```python
# config/world_building.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorldBuildingConfig(BaseSettings):
    """World-building: the SETTING for the station.

    Defines the narrative universe and context.
    Separate from AnnouncerPersonalityConfig (the CHARACTER).
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    world_setting: str = Field(
        default="laid-back tropical island paradise",
        description="The world/universe setting for the station"
    )
    world_tone: str = Field(
        default="relaxed, friendly, warm, good vibes only, island time",
        description="Emotional tone and vibe of your station"
    )
    world_framing: str = Field(
        default="Broadcasting from our little slice of paradise. The news and weather filtered through the lens of island living - warm sun, cool breezes, and the sound of waves. We keep it real but keep it chill.",
        description="How to frame all content through your station's personality"
    )
```

**Design Rationale:** This is the SETTING. Character vs Setting split is architecturally correct and provides flexibility for different announcers in the same world.

### 6. ContentSourcesConfig - Data Sources

**Responsibility:** NWS weather, RSS feeds, news settings, hallucination config

```python
# config/content_sources.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class ContentSourcesConfig(BaseSettings):
    """External content sources configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    # NWS Weather
    nws_office: Optional[str] = Field(default=None, description="NWS office code")
    nws_grid_x: Optional[int] = Field(default=None, description="NWS grid X coordinate")
    nws_grid_y: Optional[int] = Field(default=None, description="NWS grid Y coordinate")

    # RSS News Feeds
    news_rss_feeds: dict[str, list[str]] = Field(
        default={
            "news": [
                "https://feeds.npr.org/1001/rss.xml",
            ],
        },
        description="Categorized RSS feed URLs for news headlines"
    )

    # Hallucinated news settings
    hallucinate_news: bool = Field(
        default=False,
        description="Generate fake news article to mix with real news"
    )
    hallucination_chance: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Probability of hallucinating news (0.0-1.0)"
    )
    hallucination_kernels: list[str] = Field(
        default=[],
        description="Seed topics for hallucinated news stories"
    )
```

### 7. TTSConfig - Text-to-Speech

**Responsibility:** TTS provider, voices, models

```python
# config/tts.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class TTSConfig(BaseSettings):
    """Text-to-speech configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    tts_provider: str = Field(
        default="gemini",
        description="TTS provider: 'openai' or 'gemini'"
    )

    # OpenAI TTS
    tts_voice: str = Field(default="alloy", description="OpenAI TTS voice")

    # Gemini TTS
    gemini_tts_model: str = Field(
        default="gemini-2.5-pro-preview-tts",
        description="Gemini TTS model"
    )
    gemini_tts_voice: str = Field(
        default="Kore",
        description="Gemini TTS voice name"
    )
```

### 8. AudioMixingConfig - Audio Production

**Responsibility:** Bed volumes, timing, fade durations, music settings

```python
# config/audio_mixing.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AudioMixingConfig(BaseSettings):
    """Audio mixing and production configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    bed_volume_db: float = Field(default=-18.0, description="Background bed volume in dB")

    # Bed timing (ride in/out)
    bed_preroll_seconds: float = Field(default=3.0, description="Bed starts before voice")
    bed_fadein_seconds: float = Field(default=2.0, description="Bed fade-in duration")
    bed_postroll_seconds: float = Field(default=5.4, description="Bed continues after voice")
    bed_fadeout_seconds: float = Field(default=3.0, description="Bed fade-out duration")

    # Music asset configuration
    music_artist: str = Field(
        default="Clint Ecker",
        description="Artist name for all ingested music (ID3 tags and database)"
    )
```

### 9. OperationalConfig - Runtime Behavior

**Responsibility:** Scheduling, process limits, retry policies

```python
# config/operational.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class OperationalConfig(BaseSettings):
    """Runtime operational parameters and scheduling."""

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
    )

    # Content generation scheduling
    break_freshness_minutes: int = Field(
        default=50,
        description="Break freshness threshold"
    )

    # Future expansion as we discover scattered operational params:
    # playlist_generation_interval_minutes: int = Field(default=60)
    # content_fetch_retry_count: int = Field(default=3)
    # content_fetch_retry_delay_seconds: float = Field(default=5.0)
    # audio_processing_timeout_seconds: int = Field(default=300)
```

**Design Rationale:** Prevents "config creep" where operational settings pollute unrelated configs. Separates *what the station is* from *how it runs*.

### Composition Root - RadioConfig

**Responsibility:** Compose all domain configs, provide unified API

```python
# config/base.py
import os
import warnings
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import PathsConfig
from .api_keys import APIKeysConfig
from .station_identity import StationIdentityConfig
from .announcer import AnnouncerPersonalityConfig
from .world_building import WorldBuildingConfig
from .content_sources import ContentSourcesConfig
from .tts import TTSConfig
from .audio_mixing import AudioMixingConfig
from .operational import OperationalConfig

class RadioConfig(BaseSettings):
    """
    Root configuration composing all domain configs.
    Maintains backward compatibility via property shims.
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_nested_delimiter="__",  # Allows RADIO_API_KEYS__LLM_API_KEY
    )

    # Domain compositions
    paths: PathsConfig = Field(default_factory=PathsConfig)
    api_keys: APIKeysConfig = Field(default_factory=APIKeysConfig)
    station: StationIdentityConfig = Field(default_factory=StationIdentityConfig)
    announcer: AnnouncerPersonalityConfig = Field(default_factory=AnnouncerPersonalityConfig)
    world: WorldBuildingConfig = Field(default_factory=WorldBuildingConfig)
    content: ContentSourcesConfig = Field(default_factory=ContentSourcesConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    audio: AudioMixingConfig = Field(default_factory=AudioMixingConfig)
    operational: OperationalConfig = Field(default_factory=OperationalConfig)

    # LLM configuration (doesn't fit cleanly in existing domains)
    llm_model: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Claude model for bulletin script generation"
    )
    weather_script_temperature: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Temperature for weather script generation"
    )
    news_script_temperature: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Temperature for news script generation"
    )

    # Icecast integration (external system, doesn't fit domain model)
    @property
    def icecast_url(self) -> str:
        return "http://localhost:8000"

    @property
    def icecast_admin_password(self) -> str:
        """Icecast admin password from environment or Icecast XML config."""
        # Try environment variable first
        password = os.getenv("ICECAST_ADMIN_PASSWORD")
        if password:
            return password

        # Read from Icecast XML config
        try:
            import xml.etree.ElementTree as ET
            icecast_config = Path("/etc/icecast2/icecast.xml")
            if icecast_config.exists():
                tree = ET.parse(icecast_config)
                root = tree.getroot()
                admin_pass_elem = root.find('.//authentication/admin-password')
                if admin_pass_elem is not None and admin_pass_elem.text:
                    return admin_pass_elem.text
        except Exception:
            pass

        return ""

    def validate_production_config(self) -> None:
        """Validate all domain production requirements."""
        self.api_keys.validate_production()
        self.station.validate_production()

    # Backward compatibility property shims (deprecated)
    @property
    def station_name(self) -> str:
        warnings.warn(
            "'config.station_name' is deprecated. Use 'config.station.station_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.station.station_name

    @property
    def base_path(self) -> Path:
        warnings.warn(
            "'config.base_path' is deprecated. Use 'config.paths.base_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.base_path

    @property
    def break_freshness_minutes(self) -> int:
        warnings.warn(
            "'config.break_freshness_minutes' is deprecated. Use 'config.operational.break_freshness_minutes' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.operational.break_freshness_minutes

    # ... additional property shims for all commonly accessed fields
```

**Key Design Decisions:**
1. **`Field(default_factory=...)`** - Ensures new instance per RadioConfig, avoids mutable default bug
2. **Immediate deprecation warnings** - Drives migration completion, prevents new debt
3. **Some fields don't fit domains** - LLM config and Icecast integration stay in RadioConfig (YAGNI - don't create domains for 2-3 fields)

### Public API

```python
# config/__init__.py
from .base import RadioConfig
from .paths import PathsConfig
from .api_keys import APIKeysConfig
from .station_identity import StationIdentityConfig
from .announcer import AnnouncerPersonalityConfig
from .world_building import WorldBuildingConfig
from .content_sources import ContentSourcesConfig
from .tts import TTSConfig
from .audio_mixing import AudioMixingConfig
from .operational import OperationalConfig

# Global singleton (backward compatibility)
config = RadioConfig()

__all__ = [
    "config",
    "RadioConfig",
    "PathsConfig",
    "APIKeysConfig",
    "StationIdentityConfig",
    "AnnouncerPersonalityConfig",
    "WorldBuildingConfig",
    "ContentSourcesConfig",
    "TTSConfig",
    "AudioMixingConfig",
    "OperationalConfig",
]
```

**Import Compatibility:**
- `from ai_radio.config import config` - Still works (global singleton)
- `from ai_radio.config import RadioConfig` - Still works
- All existing imports continue working

## Migration Strategy

### Phase 1: Create Package Structure (No Breaking Changes)

1. Create `src/ai_radio/config/` directory
2. Create all domain config files (paths.py, api_keys.py, etc.)
3. Create base.py with empty RadioConfig composition
4. Create __init__.py with exports
5. All files exist but aren't used yet

**Status after Phase 1:** No functional changes, old config.py still works

### Phase 2: Extract One Domain at a Time

For each domain (recommend order: paths → api_keys → announcer → ...):

1. Move fields from old config.py to domain config
2. Add domain to RadioConfig composition: `paths: PathsConfig = Field(default_factory=PathsConfig)`
3. Add property shims with deprecation warnings for moved fields
4. Run tests - should pass with warnings
5. Commit

**Example Migration - PathsConfig:**

```python
# Step 1: Move base_path to PathsConfig
class PathsConfig(BaseSettings):
    base_path: Path = Field(default=Path("/srv/ai_radio"))

# Step 2: Add to RadioConfig
class RadioConfig(BaseSettings):
    paths: PathsConfig = Field(default_factory=PathsConfig)

    # Old field still exists temporarily
    base_path: Path = Field(default=Path("/srv/ai_radio"))

# Step 3: Add deprecation shim
    @property
    def base_path(self) -> Path:
        warnings.warn(
            "'config.base_path' is deprecated. Use 'config.paths.base_path'.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.base_path

# Step 4: Run tests (pass with warnings)
# Step 5: Commit
```

**Status after each domain:** One domain extracted, tests passing, old API works with warnings

### Phase 3: Update Callers Gradually

Change imports one module at a time:
- `config.base_path` → `config.paths.base_path`
- `config.station_name` → `config.station.station_name`
- `config.llm_api_key` → `config.api_keys.llm_api_key.get_secret_value()`

Tests provide safety net - warnings show what needs updating.

**No rush** - old API works indefinitely during migration.

### Phase 4: Remove Shims

After all code updated:
1. Remove deprecated property methods
2. Delete old monolithic fields from RadioConfig
3. Clean, decomposed config complete

## Testing Strategy

### Unit Tests for Each Domain Config

```python
# tests/config/test_paths_config.py
from pathlib import Path
from ai_radio.config import PathsConfig

def test_paths_config_defaults():
    """PathsConfig should have sensible defaults."""
    paths = PathsConfig()
    assert paths.base_path == Path("/srv/ai_radio")
    assert paths.assets_path == paths.base_path / "assets"
    assert paths.music_path == paths.assets_path / "music"

def test_paths_config_from_env(monkeypatch):
    """PathsConfig should load from RADIO_BASE_PATH env var."""
    monkeypatch.setenv("RADIO_BASE_PATH", "/tmp/radio")
    paths = PathsConfig()
    assert paths.base_path == Path("/tmp/radio")
    assert paths.music_path == Path("/tmp/radio/assets/music")

def test_paths_config_derived_properties():
    """Derived paths should compute correctly."""
    paths = PathsConfig(base_path=Path("/custom"))
    assert paths.breaks_path == Path("/custom/assets/breaks")
    assert paths.breaks_archive_path == Path("/custom/assets/breaks/archive")
```

### Integration Tests for RadioConfig Composition

```python
# tests/config/test_radio_config.py
from ai_radio.config import RadioConfig, PathsConfig, APIKeysConfig
import pytest

def test_radio_config_composition():
    """RadioConfig should compose all domain configs."""
    config = RadioConfig()
    assert isinstance(config.paths, PathsConfig)
    assert isinstance(config.api_keys, APIKeysConfig)
    # ... assert all domains exist

def test_production_validation():
    """validate_production_config should check all domains."""
    config = RadioConfig()
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        config.validate_production_config()

def test_production_validation_success(monkeypatch):
    """validate_production_config should pass with all required fields."""
    monkeypatch.setenv("RADIO_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RADIO_TTS_API_KEY", "test-key")
    monkeypatch.setenv("RADIO_STATION_LAT", "21.3")
    monkeypatch.setenv("RADIO_STATION_LON", "-157.8")

    config = RadioConfig()
    config.validate_production_config()  # Should not raise
```

### Test Isolation (Key Benefit)

```python
def test_content_generation():
    """Test content logic with custom config."""
    test_config = RadioConfig(
        content=ContentSourcesConfig(
            news_rss_feeds={"test": ["http://test.com/rss"]}
        )
    )
    # Test uses isolated config, doesn't affect global
    result = generate_content(test_config.content)
    assert result is not None
```

### Backward Compatibility Tests

```python
def test_deprecated_property_shims():
    """Deprecated properties should work with warnings."""
    config = RadioConfig()

    with pytest.warns(DeprecationWarning, match="station_name"):
        name = config.station_name

    assert name == config.station.station_name

def test_deprecated_base_path():
    """Deprecated base_path should work with warning."""
    config = RadioConfig()

    with pytest.warns(DeprecationWarning, match="base_path"):
        path = config.base_path

    assert path == config.paths.base_path
```

## Benefits

### 1. Clarity
- **Before:** 337 lines, everything mixed together
- **After:** 9 focused domains (~30-50 lines each), clear boundaries

### 2. Testability
- **Before:** Global singleton, hard to test with different configs
- **After:** Easy to create isolated test configs, inject into functions

```python
# Old: Hard to test
def test_scheduler():
    global config
    old_val = config.break_interval
    config.break_interval = 300  # Mutate global
    # ... test ...
    config.break_interval = old_val  # Cleanup

# New: Easy to test
def test_scheduler():
    test_config = RadioConfig(
        operational=OperationalConfig(break_interval=300)
    )
    scheduler = Scheduler(test_config.operational)
    # ... test ...
```

### 3. Security
- **Before:** API keys as plain strings, logged in errors
- **After:** SecretStr protection, never logged, segregated in APIKeysConfig

### 4. Validation
- **Before:** Errors discovered at runtime when accessing missing config
- **After:** Load-time validation catches errors immediately at startup

### 5. Maintainability
- **Before:** "Where does this setting go?" → Everything in one file
- **After:** Clear domain boundaries, easy to find related settings

### 6. Type Safety
- **Before:** Some fields untyped or loosely typed
- **After:** Full type hints throughout, Pydantic validation

### 7. Migration Safety
- **Before:** Big bang refactor, all or nothing
- **After:** Gradual migration, old code works indefinitely

## Non-Goals & Deferred Decisions

### Environment-Specific Configs (Deferred)
- **Decision:** Skip separate dev/prod/test configs for now
- **Rationale:** Current system uses defaults + env vars, no real "environment" differences exist today
- **Future:** Can add later if we actually need different settings per environment (YAGNI)

### Computed Paths as Service (Deferred)
- **Decision:** Keep derived paths as `@property` methods
- **Rationale:** Maintains current API, easier migration
- **Future:** Can extract PathService later if needed

### Dependency Injection (Deferred)
- **Decision:** Keep global singleton for now
- **Rationale:** Existing code relies on it, backward compatibility priority
- **Future:** Can migrate to DI pattern after domain decomposition complete

## Risk Assessment

### Low Risk
- **Backward compatibility preserved** - Old imports continue working
- **Gradual migration** - Can deploy after each domain extraction
- **Test coverage** - Each phase independently testable

### Medium Risk
- **Property shim coverage** - Must identify all commonly accessed fields
- **Mitigation:** Run test suite with warnings, fix as warnings appear

### Mitigation Strategies
1. **Phase 1 is risk-free** - Just creating structure, no functional changes
2. **Each domain extraction is independent** - Can stop and revert if issues arise
3. **Deprecation warnings guide migration** - Developers see exactly what to change
4. **Old API works indefinitely** - No pressure to complete migration quickly

## Success Criteria

1. ✅ **All 9 domain configs created and tested**
2. ✅ **RadioConfig composes all domains correctly**
3. ✅ **All existing tests pass (with deprecation warnings)**
4. ✅ **New domain-specific tests added and passing**
5. ✅ **Backward compatibility shims in place with warnings**
6. ✅ **Documentation updated** (this design doc + API docs)
7. ✅ **At least one module migrated** to new API (demonstrates pattern)

## Timeline Estimate

- **Phase 1** (Package structure): 1 day
- **Phase 2** (Extract domains): 4-5 days (one domain per day, ~9 domains)
- **Phase 3** (Update callers): Ongoing, gradual (weeks)
- **Phase 4** (Remove shims): 1-2 days after all callers updated

**Total:** ~2 weeks for core refactor, gradual migration afterward

## Related Work

### Dependencies
- None - This is a foundational refactor

### Dependents
- **All systems** use configuration - This refactor enables cleaner architecture across the board
- Benefits future refactors (Issue #10-#16) by establishing clear domain boundaries

## References

- Issue #14: https://github.com/clintecker/clanker-radio/issues/14
- PAL Expert Consultation: Character vs Setting architectural pattern
- Pydantic Settings Documentation: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Appendix: Full Field Mapping

### Current config.py → New Domain Configs

**PathsConfig:**
- base_path
- All @property derived paths (assets_path, music_path, beds_path, breaks_path, bumpers_path, safety_path, drops_path, tmp_path, public_path, state_path, db_path, logs_path, liquidsoap_sock_path, startup_path, breaks_archive_path, recent_weather_phrases_path)

**APIKeysConfig:**
- llm_api_key (→ SecretStr)
- tts_api_key (→ SecretStr)
- gemini_api_key (→ SecretStr)

**StationIdentityConfig:**
- station_name
- station_location
- station_tz
- station_lat
- station_lon

**AnnouncerPersonalityConfig:**
- announcer_name
- energy_level
- vibe_keywords
- max_riffs_per_break
- max_exclamations_per_break
- unhinged_percentage
- humor_priority
- allowed_comedy
- banned_comedy
- unhinged_triggers
- sentence_length_target
- max_adjectives_per_sentence
- natural_disfluency
- banned_ai_phrases
- weather_structure
- weather_translation_rules
- news_tone
- news_format
- accent_style
- delivery_style
- radio_resets
- listener_relationship

**WorldBuildingConfig:**
- world_setting
- world_tone
- world_framing

**ContentSourcesConfig:**
- nws_office
- nws_grid_x
- nws_grid_y
- news_rss_feeds
- hallucinate_news
- hallucination_chance
- hallucination_kernels

**TTSConfig:**
- tts_provider
- tts_voice
- gemini_tts_model
- gemini_tts_voice

**AudioMixingConfig:**
- bed_volume_db
- bed_preroll_seconds
- bed_fadein_seconds
- bed_postroll_seconds
- bed_fadeout_seconds
- music_artist

**OperationalConfig:**
- break_freshness_minutes

**Remaining in RadioConfig:**
- llm_model
- weather_script_temperature
- news_script_temperature
- icecast_url (@property)
- icecast_admin_password (@property)

---

**End of Design Document**
