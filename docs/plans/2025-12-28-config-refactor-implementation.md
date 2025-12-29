# Configuration System Refactor - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decompose 337-line config.py monolith into 9 testable, maintainable domain configs with full backward compatibility

**Architecture:** Gradual extraction using TDD - create package structure, then extract one domain at a time with tests, composition, and deprecation shims. Each domain is independently tested and committed.

**Tech Stack:** Python 3.12, Pydantic 2.x, pydantic-settings, pytest

---

## Overview

This plan implements the design from `docs/plans/2025-12-28-config-refactor-design.md`. We extract 9 domain configs from the monolithic `config.py`:

1. PathsConfig - Filesystem paths
2. APIKeysConfig - Secrets with SecretStr
3. StationIdentityConfig - Station metadata
4. AnnouncerPersonalityConfig - Character (87 lines)
5. WorldBuildingConfig - Setting
6. ContentSourcesConfig - Data sources
7. TTSConfig - Text-to-speech
8. AudioMixingConfig - Audio production
9. OperationalConfig - Runtime behavior

**Migration Strategy:** Create structure → Extract each domain with TDD → Add composition → Add deprecation shims → Commit

---

## Task 1: Create Config Package Structure

**Goal:** Set up the config package without breaking existing code

**Files:**
- Create: `src/ai_radio/config/__init__.py`
- Create: `src/ai_radio/config/base.py`
- Create: `tests/config/__init__.py`
- Modify: `src/ai_radio/config.py` (will become deprecated)

### Step 1: Create config package directory

```bash
mkdir -p src/ai_radio/config
mkdir -p tests/config
```

### Step 2: Create empty __init__.py for config package

```bash
touch src/ai_radio/config/__init__.py
```

### Step 3: Create empty __init__.py for config tests

```bash
touch tests/config/__init__.py
```

### Step 4: Create stub base.py

Create: `src/ai_radio/config/base.py`

```python
"""Configuration composition root (to be populated)."""
from pydantic_settings import BaseSettings

class RadioConfig(BaseSettings):
    """Root configuration - will compose domain configs."""
    pass
```

### Step 5: Update config/__init__.py to maintain backward compatibility

Create: `src/ai_radio/config/__init__.py`

```python
"""Configuration package for AI Radio Station.

This package replaces the monolithic config.py with domain-specific configs.
For backward compatibility, we re-export the old RadioConfig.
"""

# During migration: import from old config.py
import sys
from pathlib import Path

# Add parent to path to import old config
old_config_path = Path(__file__).parent.parent
sys.path.insert(0, str(old_config_path))

try:
    from config import RadioConfig as OldRadioConfig, config as old_config
    # Re-export for backward compatibility
    RadioConfig = OldRadioConfig
    config = old_config
except ImportError:
    # Fallback if old config.py is gone
    from .base import RadioConfig
    config = RadioConfig()

__all__ = ["config", "RadioConfig"]
```

### Step 6: Run tests to verify nothing broke

Run: `uv run pytest -v`
Expected: All tests pass (136 passed, 13 skipped)

### Step 7: Commit

```bash
git add src/ai_radio/config/ tests/config/
git commit -m "feat(config): create config package structure

- Add config/ package with backward compatibility
- Stub base.py for future RadioConfig composition
- Re-export old config for seamless migration

Related: #14"
```

---

## Task 2: Extract PathsConfig

**Goal:** Move all filesystem paths into PathsConfig with tests

**Files:**
- Create: `src/ai_radio/config/paths.py`
- Create: `tests/config/test_paths_config.py`

### Step 1: Write failing tests for PathsConfig

Create: `tests/config/test_paths_config.py`

```python
"""Tests for PathsConfig - filesystem paths configuration."""
from pathlib import Path
import pytest
from ai_radio.config.paths import PathsConfig


class TestPathsConfig:
    """Tests for PathsConfig."""

    def test_default_base_path(self):
        """PathsConfig should have default base_path."""
        paths = PathsConfig()
        assert paths.base_path == Path("/srv/ai_radio")

    def test_base_path_from_env(self, monkeypatch):
        """PathsConfig should load base_path from RADIO_BASE_PATH env var."""
        monkeypatch.setenv("RADIO_BASE_PATH", "/tmp/radio")
        paths = PathsConfig()
        assert paths.base_path == Path("/tmp/radio")

    def test_assets_path_derived(self):
        """assets_path should derive from base_path."""
        paths = PathsConfig(base_path=Path("/custom"))
        assert paths.assets_path == Path("/custom/assets")

    def test_music_path_derived(self):
        """music_path should derive from assets_path."""
        paths = PathsConfig(base_path=Path("/custom"))
        assert paths.music_path == Path("/custom/assets/music")

    def test_breaks_path_derived(self):
        """breaks_path should derive from assets_path."""
        paths = PathsConfig(base_path=Path("/custom"))
        assert paths.breaks_path == Path("/custom/assets/breaks")

    def test_breaks_archive_path_derived(self):
        """breaks_archive_path should derive from breaks_path."""
        paths = PathsConfig(base_path=Path("/custom"))
        assert paths.breaks_archive_path == Path("/custom/assets/breaks/archive")

    def test_db_path_derived(self):
        """db_path should derive from base_path."""
        paths = PathsConfig(base_path=Path("/custom"))
        assert paths.db_path == Path("/custom/db/radio.sqlite3")

    def test_all_derived_paths(self):
        """Verify all derived path properties exist and compute correctly."""
        paths = PathsConfig(base_path=Path("/test"))

        # Verify all properties exist and return Paths
        assert isinstance(paths.assets_path, Path)
        assert isinstance(paths.music_path, Path)
        assert isinstance(paths.beds_path, Path)
        assert isinstance(paths.breaks_path, Path)
        assert isinstance(paths.breaks_archive_path, Path)
        assert isinstance(paths.bumpers_path, Path)
        assert isinstance(paths.safety_path, Path)
        assert isinstance(paths.startup_path, Path)
        assert isinstance(paths.drops_path, Path)
        assert isinstance(paths.tmp_path, Path)
        assert isinstance(paths.public_path, Path)
        assert isinstance(paths.state_path, Path)
        assert isinstance(paths.recent_weather_phrases_path, Path)
        assert isinstance(paths.db_path, Path)
        assert isinstance(paths.logs_path, Path)
        assert isinstance(paths.liquidsoap_sock_path, Path)
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/config/test_paths_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.config.paths'"

### Step 3: Create PathsConfig implementation

Create: `src/ai_radio/config/paths.py`

```python
"""Filesystem paths configuration."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PathsConfig(BaseSettings):
    """Filesystem paths configuration.

    All filesystem paths used by the radio station.
    Derived paths are computed as properties from base_path.
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Derived paths as properties (maintains current API)

    @property
    def assets_path(self) -> Path:
        """Root directory for all audio assets."""
        return self.base_path / "assets"

    @property
    def music_path(self) -> Path:
        """Directory for music tracks."""
        return self.assets_path / "music"

    @property
    def beds_path(self) -> Path:
        """Directory for background bed music."""
        return self.assets_path / "beds"

    @property
    def breaks_path(self) -> Path:
        """Directory for generated break segments."""
        return self.assets_path / "breaks"

    @property
    def breaks_archive_path(self) -> Path:
        """Archive directory for old breaks."""
        return self.breaks_path / "archive"

    @property
    def bumpers_path(self) -> Path:
        """Directory for station ID bumpers."""
        return self.assets_path / "bumpers"

    @property
    def safety_path(self) -> Path:
        """Directory for safety/fallback audio."""
        return self.assets_path / "safety"

    @property
    def startup_path(self) -> Path:
        """Path to startup sound file."""
        return self.assets_path / "startup.mp3"

    @property
    def drops_path(self) -> Path:
        """Directory for audio drops."""
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        """Directory for temporary files."""
        return self.base_path / "tmp"

    @property
    def public_path(self) -> Path:
        """Directory for public web files."""
        return self.base_path / "public"

    @property
    def state_path(self) -> Path:
        """Directory for application state."""
        return self.base_path / "state"

    @property
    def recent_weather_phrases_path(self) -> Path:
        """Path to recent weather phrases cache."""
        return self.state_path / "recent_weather_phrases.json"

    @property
    def db_path(self) -> Path:
        """Path to SQLite database."""
        return self.base_path / "db" / "radio.sqlite3"

    @property
    def logs_path(self) -> Path:
        """Path to job logs."""
        return self.base_path / "logs" / "jobs.jsonl"

    @property
    def liquidsoap_sock_path(self) -> Path:
        """Path to Liquidsoap control socket."""
        return Path("/run/liquidsoap/radio.sock")
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/config/test_paths_config.py -v`
Expected: All 9 tests PASS

### Step 5: Commit

```bash
git add src/ai_radio/config/paths.py tests/config/test_paths_config.py
git commit -m "feat(config): add PathsConfig with full test coverage

- Extract filesystem paths from monolithic config
- All derived paths as @property methods
- 9 tests covering defaults, env vars, and derivations

Related: #14"
```

---

## Task 3: Extract APIKeysConfig

**Goal:** Move all API keys into APIKeysConfig with SecretStr protection

**Files:**
- Create: `src/ai_radio/config/api_keys.py`
- Create: `tests/config/test_api_keys_config.py`

### Step 1: Write failing tests for APIKeysConfig

Create: `tests/config/test_api_keys_config.py`

```python
"""Tests for APIKeysConfig - API keys and secrets."""
from pydantic import SecretStr
import pytest
from ai_radio.config.api_keys import APIKeysConfig


class TestAPIKeysConfig:
    """Tests for APIKeysConfig."""

    def test_defaults_are_none(self):
        """API keys should default to None."""
        api_keys = APIKeysConfig()
        assert api_keys.llm_api_key is None
        assert api_keys.tts_api_key is None
        assert api_keys.gemini_api_key is None

    def test_llm_api_key_from_env(self, monkeypatch):
        """llm_api_key should load from RADIO_LLM_API_KEY env var."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-llm-key")
        api_keys = APIKeysConfig()
        assert api_keys.llm_api_key is not None
        assert isinstance(api_keys.llm_api_key, SecretStr)
        assert api_keys.llm_api_key.get_secret_value() == "test-llm-key"

    def test_tts_api_key_from_env(self, monkeypatch):
        """tts_api_key should load from RADIO_TTS_API_KEY env var."""
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-tts-key")
        api_keys = APIKeysConfig()
        assert api_keys.tts_api_key is not None
        assert api_keys.tts_api_key.get_secret_value() == "test-tts-key"

    def test_gemini_api_key_from_env(self, monkeypatch):
        """gemini_api_key should load from RADIO_GEMINI_API_KEY env var."""
        monkeypatch.setenv("RADIO_GEMINI_API_KEY", "test-gemini-key")
        api_keys = APIKeysConfig()
        assert api_keys.gemini_api_key is not None
        assert api_keys.gemini_api_key.get_secret_value() == "test-gemini-key"

    def test_secrets_not_exposed_in_repr(self):
        """SecretStr should mask secrets in repr."""
        api_keys = APIKeysConfig(
            llm_api_key=SecretStr("secret-key")
        )
        assert "secret-key" not in repr(api_keys)
        assert "secret-key" not in str(api_keys)

    def test_validate_production_fails_without_keys(self):
        """validate_production should fail when required keys missing."""
        api_keys = APIKeysConfig()
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            api_keys.validate_production()

    def test_validate_production_fails_without_tts_key(self, monkeypatch):
        """validate_production should fail when TTS key missing."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-key")
        api_keys = APIKeysConfig()
        with pytest.raises(ValueError, match="TTS_API_KEY"):
            api_keys.validate_production()

    def test_validate_production_succeeds_with_all_keys(self, monkeypatch):
        """validate_production should succeed with all required keys."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-llm")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-tts")
        api_keys = APIKeysConfig()
        api_keys.validate_production()  # Should not raise
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/config/test_api_keys_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.config.api_keys'"

### Step 3: Create APIKeysConfig implementation

Create: `src/ai_radio/config/api_keys.py`

```python
"""API keys and secrets configuration."""
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIKeysConfig(BaseSettings):
    """API keys and secrets configuration.

    All secrets are stored as SecretStr for protection.
    Secrets are never logged or exposed in error messages.
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    llm_api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for LLM provider (Claude)"
    )
    tts_api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for OpenAI TTS"
    )
    gemini_api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for Google Gemini"
    )

    def validate_production(self) -> None:
        """Validate that required production keys are set.

        Raises:
            ValueError: If required keys are missing
        """
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

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/config/test_api_keys_config.py -v`
Expected: All 9 tests PASS

### Step 5: Commit

```bash
git add src/ai_radio/config/api_keys.py tests/config/test_api_keys_config.py
git commit -m "feat(config): add APIKeysConfig with SecretStr protection

- Extract API keys from monolithic config
- Use SecretStr for secret protection
- Production validation method
- 9 tests covering defaults, env vars, validation

Related: #14"
```

---

## Task 4: Extract Remaining Domain Configs

**Goal:** Create remaining 7 domain configs following the same TDD pattern

**Note:** The following tasks follow the same pattern as Tasks 2-3. For brevity, we'll create multiple configs per task but still follow TDD (tests first, then implementation).

### Task 4.1: StationIdentityConfig

**Files:**
- Create: `src/ai_radio/config/station_identity.py`
- Create: `tests/config/test_station_identity_config.py`

**Implementation Steps:**
1. Write tests (defaults, env vars, production validation)
2. Run tests (should fail)
3. Implement StationIdentityConfig
4. Run tests (should pass)
5. Commit

**Test Coverage:**
- Default station_name, station_location, station_tz
- Load from env vars
- Production validation (lat/lon required)

**Commit Message:**
```
feat(config): add StationIdentityConfig with validation

- Extract station metadata from monolithic config
- Production validation for lat/lon coordinates
- Full test coverage

Related: #14
```

### Task 4.2: AnnouncerPersonalityConfig

**Files:**
- Create: `src/ai_radio/config/announcer.py`
- Create: `tests/config/test_announcer_config.py`

**Implementation Steps:**
1. Write tests for core persona fields
2. Write tests for chaos budget fields
3. Write tests for humor guardrails
4. Write tests for style fields
5. Run tests (should fail)
6. Implement AnnouncerPersonalityConfig (87 lines from old config)
7. Run tests (should pass)
8. Commit

**Test Coverage:**
- Default announcer_name, energy_level, vibe_keywords
- Chaos budget (max_riffs, max_exclamations, unhinged_percentage)
- Humor guardrails (humor_priority, allowed_comedy, banned_comedy)
- Style fields (accent_style, delivery_style, radio_resets)

**Commit Message:**
```
feat(config): add AnnouncerPersonalityConfig (87 lines)

- Extract announcer persona from monolithic config
- Character definition separate from setting
- Chaos budget, humor guardrails, style controls
- Full test coverage

Related: #14
```

### Task 4.3: WorldBuildingConfig

**Files:**
- Create: `src/ai_radio/config/world_building.py`
- Create: `tests/config/test_world_building_config.py`

**Test Coverage:**
- Default world_setting, world_tone, world_framing
- Load from env vars

**Commit Message:**
```
feat(config): add WorldBuildingConfig

- Extract world setting from monolithic config
- Setting definition separate from character
- Full test coverage

Related: #14
```

### Task 4.4: ContentSourcesConfig

**Files:**
- Create: `src/ai_radio/config/content_sources.py`
- Create: `tests/config/test_content_sources_config.py`

**Test Coverage:**
- NWS weather fields (nws_office, nws_grid_x, nws_grid_y)
- RSS feeds (news_rss_feeds dict)
- Hallucination settings (hallucinate_news, hallucination_chance, hallucination_kernels)

**Commit Message:**
```
feat(config): add ContentSourcesConfig

- Extract content sources from monolithic config
- NWS weather, RSS feeds, hallucination settings
- Full test coverage

Related: #14
```

### Task 4.5: TTSConfig

**Files:**
- Create: `src/ai_radio/config/tts.py`
- Create: `tests/config/test_tts_config.py`

**Test Coverage:**
- TTS provider (default "gemini")
- OpenAI settings (tts_voice)
- Gemini settings (gemini_tts_model, gemini_tts_voice)

**Commit Message:**
```
feat(config): add TTSConfig

- Extract TTS settings from monolithic config
- OpenAI and Gemini provider configs
- Full test coverage

Related: #14
```

### Task 4.6: AudioMixingConfig

**Files:**
- Create: `src/ai_radio/config/audio_mixing.py`
- Create: `tests/config/test_audio_mixing_config.py`

**Test Coverage:**
- Bed volume (bed_volume_db)
- Bed timing (preroll, fadein, postroll, fadeout)
- Music settings (music_artist)

**Commit Message:**
```
feat(config): add AudioMixingConfig

- Extract audio mixing settings from monolithic config
- Bed volumes, timing, music artist
- Full test coverage

Related: #14
```

### Task 4.7: OperationalConfig

**Files:**
- Create: `src/ai_radio/config/operational.py`
- Create: `tests/config/test_operational_config.py`

**Test Coverage:**
- break_freshness_minutes default and env var

**Commit Message:**
```
feat(config): add OperationalConfig

- Extract operational settings from monolithic config
- Runtime behavior and scheduling
- Full test coverage

Related: #14
```

---

## Task 5: Compose All Domains in RadioConfig

**Goal:** Create new RadioConfig that composes all 9 domain configs

**Files:**
- Modify: `src/ai_radio/config/base.py`
- Create: `tests/config/test_radio_config.py`

### Step 1: Write failing tests for RadioConfig composition

Create: `tests/config/test_radio_config.py`

```python
"""Tests for RadioConfig - composition root."""
import pytest
from ai_radio.config.base import RadioConfig
from ai_radio.config.paths import PathsConfig
from ai_radio.config.api_keys import APIKeysConfig
from ai_radio.config.station_identity import StationIdentityConfig
from ai_radio.config.announcer import AnnouncerPersonalityConfig
from ai_radio.config.world_building import WorldBuildingConfig
from ai_radio.config.content_sources import ContentSourcesConfig
from ai_radio.config.tts import TTSConfig
from ai_radio.config.audio_mixing import AudioMixingConfig
from ai_radio.config.operational import OperationalConfig


class TestRadioConfigComposition:
    """Tests for RadioConfig composition."""

    def test_composes_all_domains(self):
        """RadioConfig should compose all 9 domain configs."""
        config = RadioConfig()

        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.api_keys, APIKeysConfig)
        assert isinstance(config.station, StationIdentityConfig)
        assert isinstance(config.announcer, AnnouncerPersonalityConfig)
        assert isinstance(config.world, WorldBuildingConfig)
        assert isinstance(config.content, ContentSourcesConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.audio, AudioMixingConfig)
        assert isinstance(config.operational, OperationalConfig)

    def test_default_factory_creates_new_instances(self):
        """Each RadioConfig should get fresh domain instances."""
        config1 = RadioConfig()
        config2 = RadioConfig()

        # Different instances
        assert config1.paths is not config2.paths
        assert config1.api_keys is not config2.api_keys

    def test_validate_production_config_calls_domains(self, monkeypatch):
        """validate_production_config should call all domain validations."""
        # Missing required fields
        config = RadioConfig()

        with pytest.raises(ValueError) as exc_info:
            config.validate_production_config()

        # Should mention missing LLM and TTS keys
        error_msg = str(exc_info.value)
        assert "LLM_API_KEY" in error_msg or "TTS_API_KEY" in error_msg

    def test_validate_production_config_succeeds(self, monkeypatch):
        """validate_production_config should succeed with all required fields."""
        monkeypatch.setenv("RADIO_LLM_API_KEY", "test-llm")
        monkeypatch.setenv("RADIO_TTS_API_KEY", "test-tts")
        monkeypatch.setenv("RADIO_STATION_LAT", "21.3")
        monkeypatch.setenv("RADIO_STATION_LON", "-157.8")

        config = RadioConfig()
        config.validate_production_config()  # Should not raise

    def test_llm_model_field_exists(self):
        """RadioConfig should have llm_model field (doesn't fit domain model)."""
        config = RadioConfig()
        assert config.llm_model == "claude-3-5-sonnet-latest"

    def test_script_temperature_fields_exist(self):
        """RadioConfig should have temperature fields."""
        config = RadioConfig()
        assert config.weather_script_temperature == 0.8
        assert config.news_script_temperature == 0.6

    def test_icecast_properties_exist(self):
        """RadioConfig should have icecast properties."""
        config = RadioConfig()
        assert config.icecast_url == "http://localhost:8000"
        assert isinstance(config.icecast_admin_password, str)
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/config/test_radio_config.py -v`
Expected: FAIL (base.py is still a stub)

### Step 3: Implement RadioConfig composition

Modify: `src/ai_radio/config/base.py`

```python
"""Configuration composition root."""
import os
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
    """Root configuration composing all domain configs.

    Composes 9 domain-specific configs into a unified configuration.
    Maintains backward compatibility via property shims.
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Allows RADIO_API_KEYS__LLM_API_KEY
        case_sensitive=False,
        extra="ignore",
    )

    # Domain compositions (using default_factory to avoid mutable default bug)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    api_keys: APIKeysConfig = Field(default_factory=APIKeysConfig)
    station: StationIdentityConfig = Field(default_factory=StationIdentityConfig)
    announcer: AnnouncerPersonalityConfig = Field(default_factory=AnnouncerPersonalityConfig)
    world: WorldBuildingConfig = Field(default_factory=WorldBuildingConfig)
    content: ContentSourcesConfig = Field(default_factory=ContentSourcesConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    audio: AudioMixingConfig = Field(default_factory=AudioMixingConfig)
    operational: OperationalConfig = Field(default_factory=OperationalConfig)

    # Fields that don't fit cleanly in existing domains (YAGNI - don't create domains for 2-3 fields)
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

    # Icecast integration (external system, doesn't fit domain model)
    @property
    def icecast_url(self) -> str:
        """Icecast server URL."""
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

        # Fallback default (for development)
        return ""

    def validate_production_config(self) -> None:
        """Validate all domain production requirements.

        Raises:
            ValueError: If required production fields are missing
        """
        self.api_keys.validate_production()
        self.station.validate_production()
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/config/test_radio_config.py -v`
Expected: All tests PASS

### Step 5: Commit

```bash
git add src/ai_radio/config/base.py tests/config/test_radio_config.py
git commit -m "feat(config): compose all 9 domains in RadioConfig

- RadioConfig now composes all domain configs
- Use Field(default_factory=...) for clean instance isolation
- Production validation delegates to domains
- Full test coverage

Related: #14"
```

---

## Task 6: Add Backward Compatibility Shims

**Goal:** Add deprecation property shims to RadioConfig for smooth migration

**Files:**
- Modify: `src/ai_radio/config/base.py`
- Create: `tests/config/test_backward_compatibility.py`

### Step 1: Write tests for backward compatibility shims

Create: `tests/config/test_backward_compatibility.py`

```python
"""Tests for backward compatibility property shims."""
import warnings
from pathlib import Path
import pytest
from ai_radio.config.base import RadioConfig


class TestBackwardCompatibility:
    """Tests for deprecated property shims."""

    def test_station_name_shim_warns(self):
        """config.station_name should work with deprecation warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="station_name.*deprecated"):
            name = config.station_name

        assert name == config.station.station_name

    def test_base_path_shim_warns(self):
        """config.base_path should work with deprecation warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="base_path.*deprecated"):
            path = config.base_path

        assert path == config.paths.base_path

    def test_break_freshness_minutes_shim_warns(self):
        """config.break_freshness_minutes should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="break_freshness_minutes.*deprecated"):
            minutes = config.break_freshness_minutes

        assert minutes == config.operational.break_freshness_minutes

    def test_llm_api_key_shim_warns(self):
        """config.llm_api_key should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="llm_api_key.*deprecated"):
            key = config.llm_api_key

        assert key == config.api_keys.llm_api_key

    def test_announcer_name_shim_warns(self):
        """config.announcer_name should work with warning."""
        config = RadioConfig()

        with pytest.warns(DeprecationWarning, match="announcer_name.*deprecated"):
            name = config.announcer_name

        assert name == config.announcer.announcer_name

    def test_multiple_shims_work(self):
        """Multiple deprecated properties should all work."""
        config = RadioConfig()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            _ = config.station_name
            _ = config.base_path
            _ = config.break_freshness_minutes

            # Should have 3 warnings
            assert len(w) == 3
            assert all(issubclass(warning.category, DeprecationWarning) for warning in w)
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/config/test_backward_compatibility.py -v`
Expected: FAIL (shims don't exist yet)

### Step 3: Add deprecation shims to RadioConfig

Modify: `src/ai_radio/config/base.py` (add at end of RadioConfig class)

```python
    # ===================================================================
    # Backward compatibility property shims (DEPRECATED)
    # Remove after all code migrated to new API
    # ===================================================================

    @property
    def station_name(self) -> str:
        """DEPRECATED: Use config.station.station_name instead."""
        warnings.warn(
            "'config.station_name' is deprecated. Use 'config.station.station_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.station.station_name

    @property
    def base_path(self) -> Path:
        """DEPRECATED: Use config.paths.base_path instead."""
        warnings.warn(
            "'config.base_path' is deprecated. Use 'config.paths.base_path' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.paths.base_path

    @property
    def break_freshness_minutes(self) -> int:
        """DEPRECATED: Use config.operational.break_freshness_minutes instead."""
        warnings.warn(
            "'config.break_freshness_minutes' is deprecated. Use 'config.operational.break_freshness_minutes' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.operational.break_freshness_minutes

    @property
    def llm_api_key(self):
        """DEPRECATED: Use config.api_keys.llm_api_key instead."""
        warnings.warn(
            "'config.llm_api_key' is deprecated. Use 'config.api_keys.llm_api_key' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.api_keys.llm_api_key

    @property
    def announcer_name(self) -> str:
        """DEPRECATED: Use config.announcer.announcer_name instead."""
        warnings.warn(
            "'config.announcer_name' is deprecated. Use 'config.announcer.announcer_name' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.announcer.announcer_name

    # TODO: Add shims for all commonly accessed fields
    # Run `grep -r "config\." src/ scripts/` to find usages
```

Add import at top of file:

```python
import warnings
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/config/test_backward_compatibility.py -v`
Expected: All tests PASS

### Step 5: Commit

```bash
git add src/ai_radio/config/base.py tests/config/test_backward_compatibility.py
git commit -m "feat(config): add backward compatibility shims with warnings

- Property shims for commonly accessed fields
- DeprecationWarning guides migration
- Old API works indefinitely during migration
- Full test coverage

Related: #14"
```

---

## Task 7: Update config/__init__.py to Use New RadioConfig

**Goal:** Switch config package to use new RadioConfig instead of old one

**Files:**
- Modify: `src/ai_radio/config/__init__.py`
- Modify: `tests/config/test_radio_config.py`

### Step 1: Write test for config package exports

Add to: `tests/config/test_radio_config.py`

```python
class TestConfigPackageExports:
    """Tests for config package __init__.py exports."""

    def test_config_singleton_exists(self):
        """config package should export config singleton."""
        from ai_radio.config import config
        assert config is not None
        assert isinstance(config, RadioConfig)

    def test_radioconfig_class_exported(self):
        """config package should export RadioConfig class."""
        from ai_radio.config import RadioConfig as ExportedRadioConfig
        assert ExportedRadioConfig is RadioConfig

    def test_all_domain_configs_exported(self):
        """config package should export all domain config classes."""
        from ai_radio.config import (
            PathsConfig,
            APIKeysConfig,
            StationIdentityConfig,
            AnnouncerPersonalityConfig,
            WorldBuildingConfig,
            ContentSourcesConfig,
            TTSConfig,
            AudioMixingConfig,
            OperationalConfig,
        )

        # All should be classes
        assert PathsConfig is not None
        assert APIKeysConfig is not None
        assert StationIdentityConfig is not None
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/config/test_radio_config.py::TestConfigPackageExports -v`
Expected: FAIL (config/__init__.py still imports old config)

### Step 3: Update config/__init__.py to use new RadioConfig

Modify: `src/ai_radio/config/__init__.py`

```python
"""Configuration package for AI Radio Station.

This package provides domain-specific configuration modules
that replace the monolithic config.py.

Usage:
    from ai_radio.config import config, RadioConfig

    # Access domain configs
    config.paths.base_path
    config.api_keys.llm_api_key
    config.station.station_name
"""

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

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/config/ -v`
Expected: All config tests PASS (may have deprecation warnings from existing code)

### Step 5: Run full test suite

Run: `uv run pytest -v`
Expected: Tests may fail if they import from old config.py, but new config tests should pass

### Step 6: Commit

```bash
git add src/ai_radio/config/__init__.py tests/config/test_radio_config.py
git commit -m "feat(config): switch to new RadioConfig in package exports

- config/__init__.py now uses new RadioConfig
- Export all domain configs
- Global config singleton uses new implementation
- Old config.py still exists for gradual migration

Related: #14"
```

---

## Task 8: Deprecate Old config.py

**Goal:** Mark old config.py as deprecated and update imports

**Files:**
- Modify: `src/ai_radio/config.py`

### Step 1: Add deprecation notice to old config.py

Modify top of: `src/ai_radio/config.py`

```python
"""Configuration management for AI Radio Station.

DEPRECATED: This module is deprecated in favor of the ai_radio.config package.
Use `from ai_radio.config import config, RadioConfig` instead.

This file will be removed in a future release.
Migration guide: docs/plans/2025-12-28-config-refactor-design.md
"""
import warnings

warnings.warn(
    "Importing from 'ai_radio.config' (config.py) is deprecated. "
    "Use 'from ai_radio.config import config, RadioConfig' instead. "
    "See docs/plans/2025-12-28-config-refactor-design.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

# Original config.py content follows...
```

### Step 2: Run tests

Run: `uv run pytest -v`
Expected: Tests pass, may see deprecation warnings

### Step 3: Commit

```bash
git add src/ai_radio/config.py
git commit -m "deprecate: mark old config.py as deprecated

- Add deprecation warning at top of file
- Point to migration guide
- File will be removed after full migration

Related: #14"
```

---

## Task 9: Update Example Module to New API

**Goal:** Demonstrate migration pattern by updating one module

**Files:**
- Modify: `scripts/enqueue_station_id.py` (example)
- Update any imports from old config

### Step 1: Find usage of old config API

```bash
grep "from ai_radio.config import config" scripts/enqueue_station_id.py
```

### Step 2: Update to new API pattern

Change:
```python
# Old
bumper_path = config.bumpers_path

# New
bumper_path = config.paths.bumpers_path
```

### Step 3: Run tests

Run: `uv run pytest tests/test_enqueue_station_id.py -v` (if tests exist)

### Step 4: Commit

```bash
git add scripts/enqueue_station_id.py
git commit -m "refactor: migrate enqueue_station_id.py to new config API

- Use config.paths.bumpers_path instead of config.bumpers_path
- Demonstrates migration pattern for other modules
- No deprecation warnings

Related: #14"
```

---

## Task 10: Document Migration Path

**Goal:** Add migration instructions for other developers

**Files:**
- Create: `docs/config-migration-guide.md`

### Step 1: Create migration guide

Create: `docs/config-migration-guide.md`

```markdown
# Configuration System Migration Guide

## Overview

The configuration system has been refactored from a 337-line monolith into 9 domain-specific configs. This guide helps you migrate your code to the new API.

## Quick Reference

| Old API | New API | Domain |
|---------|---------|--------|
| `config.base_path` | `config.paths.base_path` | PathsConfig |
| `config.music_path` | `config.paths.music_path` | PathsConfig |
| `config.llm_api_key` | `config.api_keys.llm_api_key.get_secret_value()` | APIKeysConfig |
| `config.station_name` | `config.station.station_name` | StationIdentityConfig |
| `config.announcer_name` | `config.announcer.announcer_name` | AnnouncerPersonalityConfig |
| `config.world_setting` | `config.world.world_setting` | WorldBuildingConfig |
| `config.nws_office` | `config.content.nws_office` | ContentSourcesConfig |
| `config.tts_voice` | `config.tts.tts_voice` | TTSConfig |
| `config.bed_volume_db` | `config.audio.bed_volume_db` | AudioMixingConfig |
| `config.break_freshness_minutes` | `config.operational.break_freshness_minutes` | OperationalConfig |

## Migration Steps

1. **Find deprecation warnings**
   ```bash
   uv run pytest -v 2>&1 | grep DeprecationWarning
   ```

2. **Update imports** (no change needed)
   ```python
   # Still works
   from ai_radio.config import config
   ```

3. **Update field access**
   ```python
   # Old
   path = config.base_path

   # New
   path = config.paths.base_path
   ```

4. **Handle SecretStr for API keys**
   ```python
   # Old
   api_key = config.llm_api_key  # str | None

   # New
   api_key = config.api_keys.llm_api_key  # SecretStr | None
   if api_key:
       key_value = api_key.get_secret_value()  # Extract actual string
   ```

5. **Run tests to verify**
   ```bash
   uv run pytest
   ```

## Benefits

- **Testability**: Easy to inject test configs
  ```python
  def test_something():
      test_config = RadioConfig(
          paths=PathsConfig(base_path=Path("/tmp/test"))
      )
      # Use test_config instead of global
  ```

- **Type Safety**: Full type hints, better IDE support

- **Security**: Secrets protected with SecretStr

- **Clarity**: Know exactly what domain a setting belongs to

## Need Help?

- Design doc: `docs/plans/2025-12-28-config-refactor-design.md`
- Implementation plan: `docs/plans/2025-12-28-config-refactor-implementation.md`
- Issue: #14
```

### Step 2: Commit

```bash
git add docs/config-migration-guide.md
git commit -m "docs: add config migration guide for developers

- Quick reference table for old → new API
- Step-by-step migration instructions
- Examples for common patterns

Related: #14"
```

---

## Task 11: Run Full Test Suite and Fix Any Issues

**Goal:** Ensure all tests pass with new config system

### Step 1: Run full test suite

Run: `uv run pytest -v`

### Step 2: Fix any failing tests

If tests fail because they use old config API:
- Update imports if needed
- Update field access to new domain structure
- Handle SecretStr for API keys

### Step 3: Check for deprecation warnings

Run: `uv run pytest -v 2>&1 | grep DeprecationWarning | sort | uniq`

Document any warnings for future cleanup.

### Step 4: Verify test count

Expected: 136 passed + new config tests (should be 170+ total)

### Step 5: Commit any fixes

```bash
git add <fixed files>
git commit -m "test: fix tests to work with new config system

- Update config API usage in tests
- Handle SecretStr in API key tests
- All tests passing

Related: #14"
```

---

## Task 12: Final Verification

**Goal:** Verify complete implementation

### Step 1: Verify all domain configs created

```bash
ls -la src/ai_radio/config/
```

Expected files:
- `__init__.py`
- `base.py`
- `paths.py`
- `api_keys.py`
- `station_identity.py`
- `announcer.py`
- `world_building.py`
- `content_sources.py`
- `tts.py`
- `audio_mixing.py`
- `operational.py`

### Step 2: Verify all tests created

```bash
ls -la tests/config/
```

Expected test files for each domain + composition + backward compat

### Step 3: Run full test suite one final time

Run: `uv run pytest -v --cov=src/ai_radio/config`

Expected: High coverage (>90%) for config package

### Step 4: Verify imports work

```bash
uv run python -c "from ai_radio.config import config, RadioConfig, PathsConfig; print('✓ Imports work')"
```

### Step 5: Create summary

Run: `git log --oneline --graph | head -20`

Verify clean commit history with descriptive messages.

---

## Success Criteria

✅ All 9 domain configs created and tested
✅ RadioConfig composes all domains correctly
✅ All existing tests pass (with deprecation warnings acceptable)
✅ New domain-specific tests added (50+ new tests)
✅ Backward compatibility shims in place
✅ Migration guide documented
✅ At least one module migrated to demonstrate pattern

## Post-Implementation Tasks

1. **Gradual Migration** (ongoing)
   - Update modules one at a time to new API
   - Remove deprecation warnings as code is updated
   - Track progress with `grep -r "config\." src/ scripts/`

2. **Remove Old config.py** (after full migration)
   - Delete `src/ai_radio/config.py`
   - Remove deprecation shims from RadioConfig
   - Update any remaining imports

3. **Documentation** (ongoing)
   - Update README if needed
   - Add API documentation for domain configs
   - Update developer onboarding docs

---

## Execution Options

**Plan complete and saved to `docs/plans/2025-12-28-config-refactor-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
