"""Tests for break generation orchestration.

Test coverage:
- Full pipeline (weather + news + script + TTS + mixing)
- Weather-only breaks
- News-only breaks
- Pipeline failure handling at each stage
- Content freshness checking (producer pattern)
- Output file naming and archival
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, call
import hashlib

import pytest

from ai_radio.break_generator import BreakGenerator, GeneratedBreak, generate_break
from ai_radio.weather import WeatherData
from ai_radio.news import NewsData, NewsHeadline
from ai_radio.script_writer import BulletinScript
from ai_radio.voice_synth import AudioFile
from ai_radio.audio_mixer import MixedAudio


class TestBreakGenerator:
    """Tests for BreakGenerator."""

    def test_initialization_uses_config(self):
        """BreakGenerator should load paths from config."""
        generator = BreakGenerator()

        assert generator.breaks_path is not None
        assert generator.beds_path is not None
        assert generator.freshness_minutes == 50

    def test_generate_full_pipeline_success(self, tmp_path):
        """generate should execute full pipeline successfully."""
        # Mock weather data
        mock_weather = WeatherData(
            temperature=72,
            conditions="Sunny",
            forecast_short="Clear skies expected.",
            timestamp=datetime.now(),
        )

        # Mock news data
        mock_news = NewsData(
            headlines=[
                NewsHeadline(title="Test Story", source="News", link="https://example.com/1")
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        # Mock bulletin script
        mock_script = BulletinScript(
            script_text="Test bulletin script",
            word_count=3,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=True,
        )

        # Mock TTS audio
        mock_voice_path = tmp_path / "voice.mp3"
        mock_voice = AudioFile(
            file_path=mock_voice_path,
            duration_estimate=45.0,
            timestamp=datetime.now(),
            voice="alloy",
            model="tts-1",
        )

        # Mock mixed audio
        mock_output_path = tmp_path / "break.mp3"
        mock_mixed = MixedAudio(
            file_path=mock_output_path,
            duration=45.0,
            timestamp=datetime.now(),
            voice_file=mock_voice_path,
            bed_file=tmp_path / "bed.mp3",
            bed_volume_db=-18.0,
            normalized=True,
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize, \
             patch("ai_radio.break_generator.mix_voice_with_bed") as mock_mix:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = mock_news
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = mock_voice
            mock_mix.return_value = mock_mixed

            generator = BreakGenerator()
            # Override paths for testing
            generator.breaks_path = tmp_path / "breaks"
            generator.beds_path = tmp_path / "beds"
            generator.tmp_path = tmp_path / "tmp"

            # Create a dummy bed file
            bed_path = tmp_path / "beds" / "bed1.mp3"
            bed_path.parent.mkdir(parents=True, exist_ok=True)
            bed_path.write_bytes(b"fake bed")

            result = generator.generate()

            # Verify all pipeline stages called
            mock_get_weather.assert_called_once()
            mock_get_news.assert_called_once()
            mock_gen_bulletin.assert_called_once_with(weather=mock_weather, news=mock_news)
            mock_synthesize.assert_called_once()
            mock_mix.assert_called_once()

            # Verify result
            assert result is not None
            assert result.file_path.parent == tmp_path / "breaks"
            assert result.file_path.name.startswith("break_")
            assert result.file_path.name.endswith(".mp3")
            assert result.duration == 45.0
            assert result.includes_weather is True
            assert result.includes_news is True

    def test_generate_weather_only(self, tmp_path):
        """generate should handle weather-only breaks."""
        mock_weather = WeatherData(
            temperature=68,
            conditions="Cloudy",
            forecast_short="Mild conditions.",
            timestamp=datetime.now(),
        )

        mock_script = BulletinScript(
            script_text="Weather update",
            word_count=2,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize, \
             patch("ai_radio.break_generator.mix_voice_with_bed") as mock_mix:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = None  # No news
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = Mock(
                file_path=tmp_path / "voice.mp3",
                duration_estimate=30.0
            )
            mock_mix.return_value = Mock(
                file_path=tmp_path / "break.mp3",
                duration=30.0,
                timestamp=datetime.now(),
            )

            generator = BreakGenerator()
            generator.breaks_path = tmp_path / "breaks"
            generator.beds_path = tmp_path / "beds"
            generator.tmp_path = tmp_path / "tmp"

            bed_path = tmp_path / "beds" / "bed1.mp3"
            bed_path.parent.mkdir(parents=True, exist_ok=True)
            bed_path.write_bytes(b"fake bed")

            result = generator.generate()

            # Verify bulletin called with weather only
            mock_gen_bulletin.assert_called_once_with(weather=mock_weather, news=None)
            assert result is not None

    def test_generate_news_only(self, tmp_path):
        """generate should handle news-only breaks."""
        mock_news = NewsData(
            headlines=[
                NewsHeadline(title="Story", source="News", link="https://example.com/1")
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        mock_script = BulletinScript(
            script_text="News update",
            word_count=2,
            timestamp=datetime.now(),
            includes_weather=False,
            includes_news=True,
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize, \
             patch("ai_radio.break_generator.mix_voice_with_bed") as mock_mix:

            mock_get_weather.return_value = None  # No weather
            mock_get_news.return_value = mock_news
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = Mock(
                file_path=tmp_path / "voice.mp3",
                duration_estimate=25.0
            )
            mock_mix.return_value = Mock(
                file_path=tmp_path / "break.mp3",
                duration=25.0,
                timestamp=datetime.now(),
            )

            generator = BreakGenerator()
            generator.breaks_path = tmp_path / "breaks"
            generator.beds_path = tmp_path / "beds"
            generator.tmp_path = tmp_path / "tmp"

            bed_path = tmp_path / "beds" / "bed1.mp3"
            bed_path.parent.mkdir(parents=True, exist_ok=True)
            bed_path.write_bytes(b"fake bed")

            result = generator.generate()

            # Verify bulletin called with news only
            mock_gen_bulletin.assert_called_once_with(weather=None, news=mock_news)
            assert result is not None

    def test_generate_no_data_fails(self):
        """generate should return None when no weather or news available."""
        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news:

            mock_get_weather.return_value = None
            mock_get_news.return_value = None

            generator = BreakGenerator()
            result = generator.generate()

            assert result is None

    def test_generate_script_generation_fails(self):
        """generate should return None when script generation fails."""
        mock_weather = WeatherData(
            temperature=70,
            conditions="Clear",
            forecast_short="Nice day.",
            timestamp=datetime.now(),
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = None
            mock_gen_bulletin.return_value = None  # Generation fails

            generator = BreakGenerator()
            result = generator.generate()

            assert result is None

    def test_generate_tts_fails(self, tmp_path):
        """generate should return None when TTS synthesis fails."""
        mock_weather = WeatherData(
            temperature=65,
            conditions="Rainy",
            forecast_short="Wet conditions.",
            timestamp=datetime.now(),
        )

        mock_script = BulletinScript(
            script_text="Test",
            word_count=1,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = None
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = None  # TTS fails

            generator = BreakGenerator()
            generator.tmp_path = tmp_path / "tmp"

            result = generator.generate()

            assert result is None

    def test_generate_mixing_fails(self, tmp_path):
        """generate should return None when audio mixing fails."""
        mock_weather = WeatherData(
            temperature=60,
            conditions="Windy",
            forecast_short="Strong winds.",
            timestamp=datetime.now(),
        )

        mock_script = BulletinScript(
            script_text="Test",
            word_count=1,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        mock_voice = AudioFile(
            file_path=tmp_path / "voice.mp3",
            duration_estimate=30.0,
            timestamp=datetime.now(),
            voice="alloy",
            model="tts-1",
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize, \
             patch("ai_radio.break_generator.mix_voice_with_bed") as mock_mix:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = None
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = mock_voice
            mock_mix.return_value = None  # Mixing fails

            generator = BreakGenerator()
            generator.breaks_path = tmp_path / "breaks"
            generator.beds_path = tmp_path / "beds"
            generator.tmp_path = tmp_path / "tmp"

            bed_path = tmp_path / "beds" / "bed1.mp3"
            bed_path.parent.mkdir(parents=True, exist_ok=True)
            bed_path.write_bytes(b"fake bed")

            result = generator.generate()

            assert result is None

    def test_generate_selects_random_bed(self, tmp_path):
        """generate should randomly select from available bed files."""
        mock_weather = WeatherData(
            temperature=75,
            conditions="Sunny",
            forecast_short="Beautiful day.",
            timestamp=datetime.now(),
        )

        mock_script = BulletinScript(
            script_text="Test",
            word_count=1,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=False,
        )

        mock_voice = AudioFile(
            file_path=tmp_path / "voice.mp3",
            duration_estimate=40.0,
            timestamp=datetime.now(),
            voice="alloy",
            model="tts-1",
        )

        with patch("ai_radio.break_generator.get_weather") as mock_get_weather, \
             patch("ai_radio.break_generator.get_news") as mock_get_news, \
             patch("ai_radio.break_generator.generate_bulletin") as mock_gen_bulletin, \
             patch("ai_radio.break_generator.synthesize_bulletin") as mock_synthesize, \
             patch("ai_radio.break_generator.mix_voice_with_bed") as mock_mix:

            mock_get_weather.return_value = mock_weather
            mock_get_news.return_value = None
            mock_gen_bulletin.return_value = mock_script
            mock_synthesize.return_value = mock_voice
            mock_mix.return_value = Mock(
                file_path=tmp_path / "break.mp3",
                duration=40.0,
                timestamp=datetime.now(),
            )

            generator = BreakGenerator()
            generator.breaks_path = tmp_path / "breaks"
            generator.beds_path = tmp_path / "beds"
            generator.tmp_path = tmp_path / "tmp"

            # Create multiple bed files
            beds_dir = tmp_path / "beds"
            beds_dir.mkdir(parents=True, exist_ok=True)
            (beds_dir / "bed1.mp3").write_bytes(b"bed1")
            (beds_dir / "bed2.mp3").write_bytes(b"bed2")
            (beds_dir / "bed3.mp3").write_bytes(b"bed3")

            result = generator.generate()

            # Verify mix was called with one of the bed files
            assert mock_mix.called
            call_kwargs = mock_mix.call_args[1]  # Get keyword arguments
            bed_arg = call_kwargs["bed_path"]
            assert bed_arg.name in ["bed1.mp3", "bed2.mp3", "bed3.mp3"]
            assert result is not None


class TestGenerateBreakConvenience:
    """Tests for generate_break() convenience function."""

    def test_generate_break_success(self):
        """generate_break should return GeneratedBreak on success."""
        mock_break = GeneratedBreak(
            file_path=Path("/tmp/break.mp3"),
            duration=45.0,
            timestamp=datetime.now(),
            includes_weather=True,
            includes_news=True,
            script_text="Test script",
        )

        with patch("ai_radio.break_generator.BreakGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate.return_value = mock_break
            mock_gen_class.return_value = mock_gen

            result = generate_break()

            assert result == mock_break

    def test_generate_break_failure(self):
        """generate_break should return None on generation failure."""
        with patch("ai_radio.break_generator.BreakGenerator") as mock_gen_class:
            mock_gen = Mock()
            mock_gen.generate.return_value = None
            mock_gen_class.return_value = mock_gen

            result = generate_break()

            assert result is None
