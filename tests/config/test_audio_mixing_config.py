"""Tests for audio mixing configuration."""

import pytest

from ai_radio.config.audio_mixing import AudioMixingConfig


class TestAudioMixingConfigDefaults:
    """Test default values for audio mixing configuration."""

    def test_bed_volume_db_default(self):
        """Test default bed volume in dB."""
        config = AudioMixingConfig()
        assert config.bed_volume_db == -18.0

    def test_bed_preroll_seconds_default(self):
        """Test default bed preroll duration."""
        config = AudioMixingConfig()
        assert config.bed_preroll_seconds == 3.0

    def test_bed_fadein_seconds_default(self):
        """Test default bed fade-in duration."""
        config = AudioMixingConfig()
        assert config.bed_fadein_seconds == 2.0

    def test_bed_postroll_seconds_default(self):
        """Test default bed postroll duration."""
        config = AudioMixingConfig()
        assert config.bed_postroll_seconds == 5.4

    def test_bed_fadeout_seconds_default(self):
        """Test default bed fade-out duration."""
        config = AudioMixingConfig()
        assert config.bed_fadeout_seconds == 3.0

    def test_music_artist_default(self):
        """Test default music artist name."""
        config = AudioMixingConfig()
        assert config.music_artist == "Clint Ecker"


class TestAudioMixingConfigEnvironment:
    """Test environment variable overrides for audio mixing configuration."""

    def test_bed_volume_db_from_env(self, monkeypatch):
        """Test bed volume can be set via environment variable."""
        monkeypatch.setenv("RADIO_BED_VOLUME_DB", "-20.0")
        config = AudioMixingConfig()
        assert config.bed_volume_db == -20.0

    def test_bed_preroll_seconds_from_env(self, monkeypatch):
        """Test bed preroll can be set via environment variable."""
        monkeypatch.setenv("RADIO_BED_PREROLL_SECONDS", "4.0")
        config = AudioMixingConfig()
        assert config.bed_preroll_seconds == 4.0

    def test_bed_fadein_seconds_from_env(self, monkeypatch):
        """Test bed fade-in can be set via environment variable."""
        monkeypatch.setenv("RADIO_BED_FADEIN_SECONDS", "2.5")
        config = AudioMixingConfig()
        assert config.bed_fadein_seconds == 2.5

    def test_bed_postroll_seconds_from_env(self, monkeypatch):
        """Test bed postroll can be set via environment variable."""
        monkeypatch.setenv("RADIO_BED_POSTROLL_SECONDS", "6.0")
        config = AudioMixingConfig()
        assert config.bed_postroll_seconds == 6.0

    def test_bed_fadeout_seconds_from_env(self, monkeypatch):
        """Test bed fade-out can be set via environment variable."""
        monkeypatch.setenv("RADIO_BED_FADEOUT_SECONDS", "3.5")
        config = AudioMixingConfig()
        assert config.bed_fadeout_seconds == 3.5

    def test_music_artist_from_env(self, monkeypatch):
        """Test music artist can be set via environment variable."""
        monkeypatch.setenv("RADIO_MUSIC_ARTIST", "Test Artist")
        config = AudioMixingConfig()
        assert config.music_artist == "Test Artist"
