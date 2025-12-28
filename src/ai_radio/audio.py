"""Audio processing utilities for asset management."""

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile

from ai_radio.config import config


@dataclass
class AudioMetadata:
    """Extracted metadata from audio file."""

    path: Path
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_sec: float = 0.0  # SOW Section 6: duration_sec

    def __post_init__(self):
        """Set defaults for missing metadata after initialization."""
        if self.title is None:
            self.title = self.path.stem  # Fallback to filename
        if self.artist is None:
            self.artist = "Unknown Artist"
        if self.album is None:
            self.album = "Unknown Album"

    @property
    def sha256_id(self) -> str:
        """Generate SHA256 hash of file contents for asset ID."""
        hasher = hashlib.sha256()
        with open(self.path, "rb") as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


def extract_metadata(file_path: Path) -> AudioMetadata:
    """Extract metadata from audio file using mutagen.

    Args:
        file_path: Path to audio file (MP3, FLAC, etc.)

    Returns:
        AudioMetadata instance with extracted information

    Raises:
        ValueError: If file cannot be read or is not a valid audio file
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")

        # Extract common tags (mutagen uses lists for tag values)
        # Handle missing tags gracefully
        title = None
        artist = None
        album = None

        if "title" in audio and audio["title"]:
            title = str(audio["title"][0])
        if "artist" in audio and audio["artist"]:
            artist = str(audio["artist"][0])
        if "album" in audio and audio["album"]:
            album = str(audio["album"][0])

        # Get duration
        duration = audio.info.length if audio.info else 0.0

        return AudioMetadata(
            path=file_path,
            title=title,
            artist=artist,
            album=album,
            duration_sec=duration,  # Store as duration_sec per SOW Section 6
        )

    except Exception as e:
        raise ValueError(f"Failed to extract metadata from {file_path}: {e}")


def set_artist_metadata(file_path: Path, artist_name: Optional[str] = None) -> None:
    """Set artist metadata on audio file ID3 tags.

    Args:
        file_path: Path to audio file to modify
        artist_name: Artist name to set (default: config.music_artist)

    Raises:
        ValueError: If file cannot be modified
    """
    if artist_name is None:
        artist_name = config.music_artist

    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")

        # Set artist tag
        audio["artist"] = [artist_name]
        audio.save()

    except Exception as e:
        raise ValueError(f"Failed to set artist metadata on {file_path}: {e}")


def normalize_audio(
    input_path: Path,
    output_path: Path,
    target_lufs: float = -18.0,
    true_peak: float = -1.0,
) -> dict:
    """Normalize audio file to broadcast standards using ffmpeg-normalize.

    After normalization, sets artist ID3 tag on output file using config.music_artist.

    Args:
        input_path: Source audio file
        output_path: Destination for normalized audio
        target_lufs: Target loudness in LUFS (default: -18.0 for broadcast)
        true_peak: True peak limit in dBTP (default: -1.0)

    Returns:
        dict with loudness_lufs and true_peak_dbtp values

    Raises:
        ValueError: If normalization fails
    """
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Run ffmpeg-normalize with EBU R128 standard
        # Use --print-stats to capture loudness measurements
        cmd = [
            "ffmpeg-normalize",
            str(input_path),
            "-o",
            str(output_path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-f",
            "--normalization-type",
            "ebu",
            "--target-level",
            str(target_lufs),
            "--true-peak",
            str(true_peak),
            "--print-stats",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 minutes - prevents hangs on malformed files
        )

        # Parse the output to extract actual OUTPUT loudness measurements
        # ffmpeg-normalize prints JSON-like stats with --print-stats
        # Check both stdout and stderr as output location varies
        output_i = None
        output_tp = None

        # Combine stdout and stderr for parsing
        combined_output = result.stdout + "\n" + result.stderr

        # Find all JSON-like blocks in output
        for line in combined_output.split("\n"):
            # Look for output measurements in JSON format
            if '"output_i":' in line:
                match = re.search(r'"output_i":\s*(-?\d+\.?\d*)', line)
                if match:
                    output_i = float(match.group(1))
            if '"output_tp":' in line:
                match = re.search(r'"output_tp":\s*(-?\d+\.?\d*)', line)
                if match:
                    output_tp = float(match.group(1))

        # Use actual output measurements, fallback to target if parsing fails
        # (parsing might fail with older ffmpeg-normalize versions)
        loudness_lufs = output_i if output_i is not None else target_lufs
        true_peak_dbtp = output_tp if output_tp is not None else true_peak

        # Set artist ID3 tag on normalized output (uses config.music_artist)
        set_artist_metadata(output_path)

        return {
            "loudness_lufs": loudness_lufs,
            "true_peak_dbtp": true_peak_dbtp,
        }

    except subprocess.TimeoutExpired:
        raise ValueError(
            f"Audio normalization timed out after 10 minutes for {input_path}"
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"Audio normalization failed for {input_path}: {e.stderr}"
        )


def measure_loudness(input_path: Path) -> dict:
    """Measure audio loudness without creating an output file.

    Uses ffmpeg-normalize in dry-run mode to get EBU R128 stats.

    Args:
        input_path: Source audio file

    Returns:
        dict with loudness_lufs and true_peak_dbtp values

    Raises:
        ValueError: If measurement fails or stats cannot be parsed
    """
    if not input_path.exists():
        raise ValueError(f"File not found: {input_path}")

    try:
        cmd = [
            "ffmpeg-normalize",
            str(input_path),
            "-n",  # No-op / dry-run mode
            "-f",  # Force overwrite
            "--normalization-type", "ebu",
            "--print-stats",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

        # Parse the output to extract INPUT loudness measurements
        # ffmpeg-normalize prints JSON-like stats with --print-stats
        # Check both stdout and stderr as output location varies
        input_i = None
        input_tp = None

        # Combine stdout and stderr for parsing
        combined_output = result.stdout + "\n" + result.stderr

        # Find all JSON-like blocks in output
        for line in combined_output.split("\n"):
            # Look for input measurements in JSON format
            if '"input_i":' in line:
                match = re.search(r'"input_i":\s*(-?\d+\.?\d*)', line)
                if match:
                    input_i = float(match.group(1))
            if '"input_tp":' in line:
                match = re.search(r'"input_tp":\s*(-?\d+\.?\d*)', line)
                if match:
                    input_tp = float(match.group(1))

        if input_i is None or input_tp is None:
            raise ValueError(
                f"Failed to parse loudness stats from ffmpeg-normalize output"
            )

        return {
            "loudness_lufs": input_i,
            "true_peak_dbtp": input_tp,
        }

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to measure loudness: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise ValueError(f"Loudness measurement timed out for {input_path}")
