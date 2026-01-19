"""Tests for show_generator.py background beds resolution."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_radio.show_generator import add_background_bed


class TestBackgroundBedResolution:
    """Tests for add_background_bed using beds_dir_resolved."""

    def test_add_background_bed_logs_warning_when_no_beds_dir_found(self, tmp_path, caplog):
        """add_background_bed should log helpful warning when beds_dir_resolved returns None."""
        voice_audio = tmp_path / "voice.mp3"
        output_path = tmp_path / "output.mp3"
        voice_audio.touch()

        # Mock config.paths.beds_dir_resolved to return None
        with patch("ai_radio.show_generator.config") as mock_config:
            mock_config.paths.beds_dir_resolved = None
            mock_config.paths.beds_path = Path("/srv/ai_radio/assets/beds")

            with caplog.at_level(logging.WARNING):
                add_background_bed(voice_audio, output_path)

            # Check that warning was logged with all checked paths
            assert "No background beds directory found" in caplog.text
            assert "$AI_RADIO_BEDS_DIR" in caplog.text
            assert "/srv/ai_radio/assets/beds" in caplog.text
            assert "~/Music/radio-beds" in caplog.text
            assert "./assets/beds" in caplog.text
            assert "/tmp/radio-beds" in caplog.text
            assert "Background music will be skipped" in caplog.text

            # Check that output file was created (copy of voice audio)
            assert output_path.exists()

    def test_add_background_bed_logs_info_when_beds_dir_found(self, tmp_path, caplog):
        """add_background_bed should log info message showing which beds directory is used."""
        voice_audio = tmp_path / "voice.mp3"
        output_path = tmp_path / "output.mp3"
        voice_audio.touch()

        # Create beds directory with a bed file
        beds_dir = tmp_path / "beds"
        beds_dir.mkdir()
        bed_file = beds_dir / "test_bed.mp3"
        bed_file.touch()

        # Mock config.paths.beds_dir_resolved to return our temp beds dir
        with patch("ai_radio.show_generator.config") as mock_config:
            mock_config.paths.beds_dir_resolved = beds_dir

            # Mock subprocess calls since we're just testing the path resolution
            with patch("ai_radio.show_generator.subprocess.run") as mock_run:
                # Mock ffprobe to return a duration
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="10.5"
                )

                with caplog.at_level(logging.INFO):
                    add_background_bed(voice_audio, output_path)

                # Check that info message was logged showing which directory is used
                assert f"Using beds directory: {beds_dir}" in caplog.text
                assert "Adding background bed:" in caplog.text

    def test_add_background_bed_skips_gracefully_when_no_bed_files(self, tmp_path, caplog):
        """add_background_bed should skip gracefully when beds dir exists but has no files."""
        voice_audio = tmp_path / "voice.mp3"
        output_path = tmp_path / "output.mp3"
        voice_audio.touch()

        # Create empty beds directory
        beds_dir = tmp_path / "beds"
        beds_dir.mkdir()

        # Mock config.paths.beds_dir_resolved to return our temp beds dir
        with patch("ai_radio.show_generator.config") as mock_config:
            mock_config.paths.beds_dir_resolved = beds_dir

            with caplog.at_level(logging.WARNING):
                add_background_bed(voice_audio, output_path)

            # Check that warning was logged
            assert f"No bed files found in {beds_dir}" in caplog.text
            assert "skipping background music" in caplog.text

            # Check that output file was created (copy of voice audio)
            assert output_path.exists()

    def test_add_background_bed_uses_environment_variable_path(self, tmp_path, monkeypatch, caplog):
        """add_background_bed should use AI_RADIO_BEDS_DIR when set."""
        voice_audio = tmp_path / "voice.mp3"
        output_path = tmp_path / "output.mp3"
        voice_audio.touch()

        # Create beds directory with a bed file
        beds_dir = tmp_path / "env_beds"
        beds_dir.mkdir()
        bed_file = beds_dir / "test_bed.mp3"
        bed_file.touch()

        # Set environment variable
        monkeypatch.setenv("AI_RADIO_BEDS_DIR", str(beds_dir))

        # Mock subprocess calls
        with patch("ai_radio.show_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="10.5"
            )

            with caplog.at_level(logging.INFO):
                add_background_bed(voice_audio, output_path)

            # Check that the environment variable path was used
            assert f"Using beds directory: {beds_dir}" in caplog.text
