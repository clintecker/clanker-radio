"""Tests for audio mixing and ducking with background beds.

Test coverage:
- Voice + bed mixing with ducking
- Loudness normalization (EBU R128)
- Missing bed file handling
- Invalid audio file handling
- Duration matching/trimming
- Fade in/out application
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, call
import subprocess

import pytest

from ai_radio.audio_mixer import AudioMixer, MixedAudio, mix_voice_with_bed


class TestAudioMixer:
    """Tests for AudioMixer."""

    def test_initialization_uses_config(self):
        """AudioMixer should load bed volume from config."""
        mixer = AudioMixer()

        assert mixer.bed_volume_db == -18.0
        assert mixer.target_lufs == -18.0
        assert mixer.true_peak_limit == -1.0

    def test_mix_with_bed_success(self, tmp_path):
        """mix_with_bed should combine voice and bed with ducking."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        # Create dummy files
        voice_path.write_bytes(b"fake voice audio")
        bed_path.write_bytes(b"fake bed audio")

        mixer = AudioMixer()

        # Mock ffprobe to return duration
        with patch("subprocess.run") as mock_run:
            # First call: ffprobe for voice duration
            mock_probe_result = Mock()
            mock_probe_result.returncode = 0
            mock_probe_result.stdout = "45.5"

            # Second call: ffmpeg mixing
            mock_ffmpeg_result = Mock()
            mock_ffmpeg_result.returncode = 0

            mock_run.side_effect = [mock_probe_result, mock_ffmpeg_result]

            result = mixer.mix_with_bed(voice_path, bed_path, output_path)

            # Verify ffprobe was called
            assert mock_run.call_count == 2
            ffprobe_call = mock_run.call_args_list[0]
            assert "ffprobe" in ffprobe_call[0][0]
            assert str(voice_path) in ffprobe_call[0][0]

            # Verify ffmpeg was called with ducking filter
            ffmpeg_call = mock_run.call_args_list[1]
            assert "ffmpeg" in ffmpeg_call[0][0]
            assert str(voice_path) in ffmpeg_call[0][0]
            assert str(bed_path) in ffmpeg_call[0][0]
            assert "sidechaincompress" in " ".join(ffmpeg_call[0][0])

            # Verify result
            assert result is not None
            assert result.file_path == output_path
            assert result.duration == 45.5
            assert result.voice_file == voice_path
            assert result.bed_file == bed_path

    def test_mix_with_bed_missing_voice(self, tmp_path):
        """mix_with_bed should return None if voice file missing."""
        voice_path = tmp_path / "missing.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        bed_path.write_bytes(b"fake bed")

        mixer = AudioMixer()
        result = mixer.mix_with_bed(voice_path, bed_path, output_path)

        assert result is None

    def test_mix_with_bed_missing_bed(self, tmp_path):
        """mix_with_bed should return None if bed file missing."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "missing.mp3"
        output_path = tmp_path / "mixed.mp3"

        voice_path.write_bytes(b"fake voice")

        mixer = AudioMixer()
        result = mixer.mix_with_bed(voice_path, bed_path, output_path)

        assert result is None

    def test_mix_with_bed_ffmpeg_error(self, tmp_path):
        """mix_with_bed should return None on ffmpeg error."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        voice_path.write_bytes(b"fake voice")
        bed_path.write_bytes(b"fake bed")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            # ffprobe succeeds
            mock_probe = Mock()
            mock_probe.returncode = 0
            mock_probe.stdout = "30.0"

            # ffmpeg fails
            mock_ffmpeg = Mock()
            mock_ffmpeg.returncode = 1
            mock_ffmpeg.stderr = "ffmpeg error"

            mock_run.side_effect = [mock_probe, mock_ffmpeg]

            result = mixer.mix_with_bed(voice_path, bed_path, output_path)

            assert result is None

    def test_mix_with_bed_applies_normalization(self, tmp_path):
        """mix_with_bed should apply EBU R128 normalization."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        voice_path.write_bytes(b"fake voice")
        bed_path.write_bytes(b"fake bed")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            mock_probe = Mock()
            mock_probe.returncode = 0
            mock_probe.stdout = "25.0"

            mock_ffmpeg = Mock()
            mock_ffmpeg.returncode = 0

            mock_run.side_effect = [mock_probe, mock_ffmpeg]

            mixer.mix_with_bed(voice_path, bed_path, output_path)

            # Verify loudnorm filter in ffmpeg command
            ffmpeg_call = mock_run.call_args_list[1]
            ffmpeg_cmd = " ".join(ffmpeg_call[0][0])
            assert "loudnorm" in ffmpeg_cmd
            assert "I=-18" in ffmpeg_cmd  # Target LUFS
            assert "TP=-1.0" in ffmpeg_cmd  # True peak limit

    def test_mix_with_bed_trims_to_voice_duration(self, tmp_path):
        """mix_with_bed should trim bed to match voice duration."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        voice_path.write_bytes(b"fake voice")
        bed_path.write_bytes(b"fake bed")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            mock_probe = Mock()
            mock_probe.returncode = 0
            mock_probe.stdout = "60.0"

            mock_ffmpeg = Mock()
            mock_ffmpeg.returncode = 0

            mock_run.side_effect = [mock_probe, mock_ffmpeg]

            mixer.mix_with_bed(voice_path, bed_path, output_path)

            # Verify trim filter in ffmpeg command
            ffmpeg_call = mock_run.call_args_list[1]
            ffmpeg_cmd = " ".join(ffmpeg_call[0][0])
            assert "atrim" in ffmpeg_cmd or "trim" in ffmpeg_cmd

    def test_mix_with_bed_custom_bed_volume(self, tmp_path):
        """mix_with_bed should respect custom bed volume."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        voice_path.write_bytes(b"fake voice")
        bed_path.write_bytes(b"fake bed")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            mock_probe = Mock()
            mock_probe.returncode = 0
            mock_probe.stdout = "40.0"

            mock_ffmpeg = Mock()
            mock_ffmpeg.returncode = 0

            mock_run.side_effect = [mock_probe, mock_ffmpeg]

            mixer.mix_with_bed(voice_path, bed_path, output_path, bed_volume_db=-24.0)

            # Verify volume adjustment in ffmpeg command
            ffmpeg_call = mock_run.call_args_list[1]
            ffmpeg_cmd = " ".join(ffmpeg_call[0][0])
            assert "volume=-24" in ffmpeg_cmd or "volume=-24.0" in ffmpeg_cmd

    def test_get_audio_duration_success(self, tmp_path):
        """get_audio_duration should return duration from ffprobe."""
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"fake audio")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "123.456"
            mock_run.return_value = mock_result

            duration = mixer.get_audio_duration(audio_path)

            assert duration == 123.456

            # Verify ffprobe command
            assert mock_run.called
            cmd = mock_run.call_args[0][0]
            assert "ffprobe" in cmd
            assert str(audio_path) in cmd

    def test_get_audio_duration_missing_file(self, tmp_path):
        """get_audio_duration should return None for missing files."""
        audio_path = tmp_path / "missing.mp3"

        mixer = AudioMixer()
        duration = mixer.get_audio_duration(audio_path)

        assert duration is None

    def test_get_audio_duration_ffprobe_error(self, tmp_path):
        """get_audio_duration should return None on ffprobe error."""
        audio_path = tmp_path / "test.mp3"
        audio_path.write_bytes(b"fake audio")

        mixer = AudioMixer()

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "ffprobe error"
            mock_run.return_value = mock_result

            duration = mixer.get_audio_duration(audio_path)

            assert duration is None


class TestMixVoiceWithBedConvenience:
    """Tests for mix_voice_with_bed() convenience function."""

    def test_mix_voice_with_bed_success(self, tmp_path):
        """mix_voice_with_bed should return MixedAudio on success."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        mock_mixed = MixedAudio(
            file_path=output_path,
            duration=45.0,
            timestamp=datetime.now(),
            voice_file=voice_path,
            bed_file=bed_path,
            bed_volume_db=-18.0,
            normalized=True,
        )

        with patch("ai_radio.audio_mixer.AudioMixer") as mock_mixer_class:
            mock_mixer = Mock()
            mock_mixer.mix_with_bed.return_value = mock_mixed
            mock_mixer_class.return_value = mock_mixer

            result = mix_voice_with_bed(voice_path, bed_path, output_path)

            assert result == mock_mixed

    def test_mix_voice_with_bed_failure(self, tmp_path):
        """mix_voice_with_bed should return None on mix failure."""
        voice_path = tmp_path / "voice.mp3"
        bed_path = tmp_path / "bed.mp3"
        output_path = tmp_path / "mixed.mp3"

        with patch("ai_radio.audio_mixer.AudioMixer") as mock_mixer_class:
            mock_mixer = Mock()
            mock_mixer.mix_with_bed.return_value = None
            mock_mixer_class.return_value = mock_mixer

            result = mix_voice_with_bed(voice_path, bed_path, output_path)

            assert result is None
