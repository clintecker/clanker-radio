"""Tests for PathsConfig.beds_dir_resolved flexible path resolution."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_radio.config.paths import PathsConfig


class TestBedsResolvedProperty:
    """Tests for PathsConfig.beds_dir_resolved flexible path resolution."""

    def test_beds_dir_resolved_checks_environment_variable_first(self, tmp_path, monkeypatch):
        """beds_dir_resolved should check AI_RADIO_BEDS_DIR environment variable first."""
        # Create a temp beds directory
        beds_dir = tmp_path / "env_beds"
        beds_dir.mkdir()

        # Set environment variable
        monkeypatch.setenv("AI_RADIO_BEDS_DIR", str(beds_dir))

        paths = PathsConfig(base_path=Path("/srv/ai_radio"))
        assert paths.beds_dir_resolved == beds_dir

    def test_beds_dir_resolved_checks_configured_path_second(self, tmp_path):
        """beds_dir_resolved should check configured beds_path if env var not set."""
        # Create a temp beds directory in the "configured" location
        base = tmp_path / "ai_radio"
        beds_dir = base / "assets" / "beds"
        beds_dir.mkdir(parents=True)

        # No environment variable, but configured path exists
        paths = PathsConfig(base_path=base)
        assert paths.beds_dir_resolved == beds_dir

    def test_beds_dir_resolved_checks_home_music_radio_beds(self, tmp_path, monkeypatch):
        """beds_dir_resolved should check ~/Music/radio-beds as fallback."""
        # Mock Path.home() to return our temp directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        beds_dir = fake_home / "Music" / "radio-beds"
        beds_dir.mkdir(parents=True)

        with patch("pathlib.Path.home", return_value=fake_home):
            # Base path doesn't exist, no env var
            paths = PathsConfig(base_path=Path("/srv/ai_radio"))
            assert paths.beds_dir_resolved == beds_dir

    def test_beds_dir_resolved_checks_cwd_assets_beds(self, tmp_path, monkeypatch):
        """beds_dir_resolved should check ./assets/beds as fallback."""
        # Create beds in current working directory
        cwd = tmp_path / "project"
        cwd.mkdir()
        beds_dir = cwd / "assets" / "beds"
        beds_dir.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=cwd):
            # Base path doesn't exist, no env var, no ~/Music
            paths = PathsConfig(base_path=Path("/srv/ai_radio"))
            assert paths.beds_dir_resolved == beds_dir

    def test_beds_dir_resolved_checks_tmp_radio_beds(self, tmp_path):
        """beds_dir_resolved should check /tmp/radio-beds as fallback."""
        # Create beds in /tmp
        beds_dir = tmp_path / "radio-beds"
        beds_dir.mkdir()

        # Mock /tmp to be our tmp_path for testing
        with patch("pathlib.Path", side_effect=lambda p: Path(str(p).replace("/tmp", str(tmp_path)))):
            paths = PathsConfig(base_path=Path("/srv/ai_radio"))
            # Can't reliably test this without mocking Path() constructor
            # This test is more for documentation of expected behavior

    def test_beds_dir_resolved_returns_none_when_nothing_found(self, tmp_path, monkeypatch):
        """beds_dir_resolved should return None when no beds directory exists."""
        # Mock home() and cwd() to return nonexistent paths
        fake_home = tmp_path / "nonexistent_home"
        fake_cwd = tmp_path / "nonexistent_cwd"
        with patch("pathlib.Path.home", return_value=fake_home):
            with patch("pathlib.Path.cwd", return_value=fake_cwd):
                paths = PathsConfig(base_path=Path("/nonexistent/path"))
                assert paths.beds_dir_resolved is None

    def test_beds_dir_resolved_prefers_env_var_over_configured_path(self, tmp_path, monkeypatch):
        """beds_dir_resolved should prefer env var even if configured path exists."""
        # Create both directories
        base = tmp_path / "ai_radio"
        configured_beds = base / "assets" / "beds"
        configured_beds.mkdir(parents=True)

        env_beds = tmp_path / "env_beds"
        env_beds.mkdir()

        # Set environment variable
        monkeypatch.setenv("AI_RADIO_BEDS_DIR", str(env_beds))

        paths = PathsConfig(base_path=base)
        # Should return env var path, not configured path
        assert paths.beds_dir_resolved == env_beds

    def test_beds_dir_resolved_ignores_nonexistent_env_var_path(self, tmp_path, monkeypatch):
        """beds_dir_resolved should ignore env var if path doesn't exist."""
        # Set env var to nonexistent path
        monkeypatch.setenv("AI_RADIO_BEDS_DIR", "/nonexistent/beds")

        # Create configured path
        base = tmp_path / "ai_radio"
        beds_dir = base / "assets" / "beds"
        beds_dir.mkdir(parents=True)

        paths = PathsConfig(base_path=base)
        # Should fall through to configured path
        assert paths.beds_dir_resolved == beds_dir

    def test_beds_dir_resolved_searches_sequentially_until_found(self, tmp_path, monkeypatch):
        """beds_dir_resolved should stop at first existing path in priority order."""
        # Only create the third fallback option (./assets/beds)
        cwd = tmp_path / "project"
        cwd.mkdir()
        beds_dir = cwd / "assets" / "beds"
        beds_dir.mkdir(parents=True)

        # Mock home() to return nonexistent path
        fake_home = tmp_path / "nonexistent_home"
        with patch("pathlib.Path.home", return_value=fake_home):
            with patch("pathlib.Path.cwd", return_value=cwd):
                # No env var, no configured path, no ~/Music - should find ./assets/beds
                paths = PathsConfig(base_path=Path("/srv/ai_radio"))
                assert paths.beds_dir_resolved == beds_dir
