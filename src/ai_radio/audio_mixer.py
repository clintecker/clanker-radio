"""Audio mixing with background beds and ducking.

Combines TTS voice audio with background music beds using ffmpeg.
Applies sidechain compression (ducking) to reduce bed volume during speech.
Normalizes output to EBU R128 broadcast standard (-18 LUFS, -1.0 dBTP).
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class MixedAudio:
    """Mixed audio file with metadata."""

    file_path: Path  # Output mixed audio file
    duration: float  # Duration in seconds
    timestamp: datetime
    voice_file: Path  # Source voice file
    bed_file: Path  # Source bed file
    bed_volume_db: float  # Bed volume in dB
    normalized: bool  # Whether loudness normalization was applied


class AudioMixer:
    """Audio mixer with ducking and normalization.

    Combines voice audio with background music beds, applies sidechain
    compression (ducking) to reduce bed volume during speech, and
    normalizes to broadcast loudness standards.
    """

    def __init__(self):
        """Initialize audio mixer with config settings."""
        self.bed_volume_db = config.bed_volume_db
        self.bed_preroll_seconds = config.bed_preroll_seconds
        self.bed_fadein_seconds = config.bed_fadein_seconds
        self.bed_postroll_seconds = config.bed_postroll_seconds
        self.bed_fadeout_seconds = config.bed_fadeout_seconds
        self.target_lufs = -18.0  # EBU R128 standard
        self.true_peak_limit = -1.0  # True peak ceiling

    def get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get duration of audio file in seconds using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds, or None if unable to determine
        """
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return None

            duration = float(result.stdout.strip())
            return duration

        except (ValueError, subprocess.SubprocessError) as e:
            logger.error(f"Failed to get audio duration: {e}")
            return None

    def mix_with_bed(
        self,
        voice_path: Path,
        bed_path: Path,
        output_path: Path,
        bed_volume_db: Optional[float] = None,
        metadata_title: Optional[str] = None,
        metadata_artist: Optional[str] = None,
    ) -> Optional[MixedAudio]:
        """Mix voice audio with background bed using ducking.

        Applies sidechain compression to duck the bed when voice is present,
        then normalizes the final mix to EBU R128 broadcast standard.

        Args:
            voice_path: Path to voice audio file (TTS output)
            bed_path: Path to background bed music file
            output_path: Path for mixed output file
            bed_volume_db: Bed volume in dB (default: from config)

        Returns:
            MixedAudio with metadata, or None if mixing fails
        """
        # Validate inputs
        if not voice_path.exists():
            logger.error(f"Voice file not found: {voice_path}")
            return None

        if not bed_path.exists():
            logger.error(f"Bed file not found: {bed_path}")
            return None

        # Get voice duration to trim bed
        voice_duration = self.get_audio_duration(voice_path)
        if voice_duration is None:
            logger.error("Cannot determine voice duration")
            return None

        # Use configured bed volume if not specified
        if bed_volume_db is None:
            bed_volume_db = self.bed_volume_db

        try:
            # Calculate timing for ride in/out
            total_duration = self.bed_preroll_seconds + voice_duration + self.bed_postroll_seconds
            fadeout_start = total_duration - self.bed_fadeout_seconds
            preroll_ms = int(self.bed_preroll_seconds * 1000)  # adelay uses milliseconds

            # Build ffmpeg filter complex for mixing with ducking and ride in/out
            # [0:a] = voice (main input)
            # [1:a] = bed (sidechain input)
            #
            # Process:
            # 1. Delay voice by preroll_seconds (so bed can start first)
            # 2. Split delayed voice for reuse (sidechain trigger + final mix)
            # 3. Trim bed to total duration, apply volume
            # 4. Apply fade-in to bed at start (ride in)
            # 5. Apply fade-out to bed at end (ride out)
            # 6. Apply sidechain compression (ducking) using delayed voice as trigger
            # 7. Mix delayed voice and ducked bed
            # 8. Normalize to EBU R128 standard
            # Convert total_duration to milliseconds for apad
            total_duration_ms = int(total_duration * 1000)

            filter_complex = (
                f"[0:a]adelay={preroll_ms}|{preroll_ms},apad=whole_dur={total_duration_ms}ms[delayed];"
                f"[delayed]asplit=2[voice_for_sidechain][voice_for_mix];"
                f"[1:a]atrim=duration={total_duration},volume={bed_volume_db}dB,"
                f"afade=t=in:st=0:d={self.bed_fadein_seconds},"
                f"afade=t=out:st={fadeout_start}:d={self.bed_fadeout_seconds}[bed];"
                f"[bed][voice_for_sidechain]sidechaincompress=threshold=0.02:ratio=3:attack=5:release=200[ducked];"
                f"[ducked][voice_for_mix]amix=inputs=2:duration=shortest[mixed];"
                f"[mixed]loudnorm=I={self.target_lufs}:TP={self.true_peak_limit}:LRA=11[normalized]"
            )

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Run ffmpeg
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-i", str(voice_path),  # Input 0: voice
                "-i", str(bed_path),  # Input 1: bed
                "-filter_complex", filter_complex,
                "-map", "[normalized]",
                "-map_metadata", "-1",  # Strip all metadata (prevents copying bed's ID3 tags)
            ]

            # Add custom metadata if provided
            if metadata_title:
                cmd.extend(["-metadata", f"title={metadata_title}"])
            if metadata_artist:
                cmd.extend(["-metadata", f"artist={metadata_artist}"])

            cmd.extend([
                "-c:a", "libmp3lame",
                "-q:a", "2",  # High quality MP3
                str(output_path),
            ])

            logger.info(f"Mixing audio: {voice_path.name} + {bed_path.name}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg mixing failed: {result.stderr}")
                return None

            logger.info(f"Mixed audio saved: {output_path}")

            return MixedAudio(
                file_path=output_path,
                duration=total_duration,
                timestamp=datetime.now(),
                voice_file=voice_path,
                bed_file=bed_path,
                bed_volume_db=bed_volume_db,
                normalized=True,
            )

        except subprocess.SubprocessError as e:
            logger.error(f"Audio mixing failed: {e}")
            return None


def mix_voice_with_bed(
    voice_path: Path,
    bed_path: Path,
    output_path: Path,
    bed_volume_db: Optional[float] = None,
    metadata_title: Optional[str] = None,
    metadata_artist: Optional[str] = None,
) -> Optional[MixedAudio]:
    """Convenience function to mix voice with background bed.

    Args:
        voice_path: Path to voice audio
        bed_path: Path to background bed
        output_path: Path for output
        bed_volume_db: Optional bed volume override
        metadata_title: Optional ID3 title tag
        metadata_artist: Optional ID3 artist tag

    Returns:
        MixedAudio or None if mixing fails
    """
    mixer = AudioMixer()
    return mixer.mix_with_bed(
        voice_path, bed_path, output_path, bed_volume_db, metadata_title, metadata_artist
    )
