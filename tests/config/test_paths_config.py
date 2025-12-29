"""Tests for PathsConfig domain configuration."""

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

    def test_derived_assets_path(self):
        """assets_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.assets_path == Path("/custom/radio/assets")

    def test_derived_music_path(self):
        """music_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.music_path == Path("/custom/radio/assets/music")

    def test_derived_beds_path(self):
        """beds_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.beds_path == Path("/custom/radio/assets/beds")

    def test_derived_breaks_path(self):
        """breaks_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.breaks_path == Path("/custom/radio/assets/breaks")

    def test_derived_breaks_archive_path(self):
        """breaks_archive_path should be derived from breaks_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.breaks_archive_path == Path("/custom/radio/assets/breaks/archive")

    def test_derived_bumpers_path(self):
        """bumpers_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.bumpers_path == Path("/custom/radio/assets/bumpers")

    def test_derived_safety_path(self):
        """safety_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.safety_path == Path("/custom/radio/assets/safety")

    def test_derived_startup_path(self):
        """startup_path should be derived from assets_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.startup_path == Path("/custom/radio/assets/startup.mp3")

    def test_derived_drops_path(self):
        """drops_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.drops_path == Path("/custom/radio/drops")

    def test_derived_tmp_path(self):
        """tmp_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.tmp_path == Path("/custom/radio/tmp")

    def test_derived_public_path(self):
        """public_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.public_path == Path("/custom/radio/public")

    def test_derived_state_path(self):
        """state_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.state_path == Path("/custom/radio/state")

    def test_derived_recent_weather_phrases_path(self):
        """recent_weather_phrases_path should be derived from state_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.recent_weather_phrases_path == Path("/custom/radio/state/recent_weather_phrases.json")

    def test_derived_db_path(self):
        """db_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.db_path == Path("/custom/radio/db/radio.sqlite3")

    def test_derived_logs_path(self):
        """logs_path should be derived from base_path."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.logs_path == Path("/custom/radio/logs/jobs.jsonl")

    def test_derived_liquidsoap_sock_path(self):
        """liquidsoap_sock_path should be hardcoded (not derived)."""
        paths = PathsConfig(base_path=Path("/custom/radio"))
        assert paths.liquidsoap_sock_path == Path("/run/liquidsoap/radio.sock")
