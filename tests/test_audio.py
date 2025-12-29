"""Tests for audio metadata extraction."""

import pytest
from pathlib import Path

from ai_radio.audio import extract_metadata, AudioMetadata, normalize_audio


def test_extract_metadata_from_test_track():
    """Test metadata extraction from known test file."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    metadata = extract_metadata(test_file)

    assert metadata.title == "Test Tone 440Hz"
    assert metadata.artist == "Test Artist"
    assert metadata.album == "Test Album"
    assert metadata.duration_sec > 29.0  # Approximately 30 seconds
    assert metadata.duration_sec < 31.0


def test_extract_metadata_nonexistent_file():
    """Test that nonexistent file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        extract_metadata(Path("/nonexistent/file.mp3"))


def test_sha256_id_generation():
    """Test SHA256 ID generation produces consistent hash."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    metadata = extract_metadata(test_file)
    sha1 = metadata.sha256_id
    sha2 = metadata.sha256_id

    assert sha1 == sha2  # Deterministic
    assert len(sha1) == 64  # SHA256 is 64 hex characters


def test_metadata_defaults_for_missing_tags():
    """Test that missing metadata tags use sensible defaults."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    metadata = extract_metadata(test_file)

    # Even if metadata is present, test the dataclass defaults work
    metadata_with_nones = AudioMetadata(
        path=Path("/some/file.mp3"),
        title=None,
        artist=None,
        album=None,
        duration_sec=100.0,
    )

    assert metadata_with_nones.title == "file"  # Filename stem
    assert metadata_with_nones.artist == "Unknown Artist"
    assert metadata_with_nones.album == "Unknown Album"


def test_normalize_audio_with_test_track():
    """Test audio normalization with test track."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    output_file = Path("/tmp/test_normalized.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    # Clean up output file if it exists
    if output_file.exists():
        output_file.unlink()

    try:
        result = normalize_audio(
            test_file,
            output_file,
            target_lufs=-18.0,
            true_peak=-1.0,
        )

        # Verify output file was created
        assert output_file.exists()

        # Verify result contains expected keys
        assert "loudness_lufs" in result
        assert "true_peak_dbtp" in result

        # Verify measurements are reasonable
        # Note: If --print-stats parsing fails, may return target values as fallback
        assert -19.0 < result["loudness_lufs"] < -17.0  # Within 1 LUFS of target
        assert -16.0 < result["true_peak_dbtp"] < -12.0  # Reasonable range for output

    finally:
        # Clean up
        if output_file.exists():
            output_file.unlink()


def test_normalize_audio_nonexistent_file():
    """Test that nonexistent input file raises ValueError."""
    with pytest.raises(ValueError, match="Input file not found"):
        normalize_audio(
            Path("/nonexistent/file.mp3"),
            Path("/tmp/output.mp3"),
        )


def test_normalize_audio_creates_output_directory():
    """Test that normalize_audio creates output directory if needed."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    output_file = Path("/tmp/test_subdir/normalized.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    # Clean up if exists
    if output_file.exists():
        output_file.unlink()
    if output_file.parent.exists():
        output_file.parent.rmdir()

    try:
        result = normalize_audio(test_file, output_file)

        # Verify directory was created
        assert output_file.parent.exists()
        assert output_file.exists()

    finally:
        # Clean up
        if output_file.exists():
            output_file.unlink()
        if output_file.parent.exists():
            output_file.parent.rmdir()


def test_measure_loudness_returns_stats(tmp_path):
    """Verify measure_loudness returns loudness stats without creating output."""
    from ai_radio.audio import measure_loudness

    # Use existing test track
    test_track = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    result = measure_loudness(test_track)

    assert "loudness_lufs" in result
    assert "true_peak_dbtp" in result
    assert isinstance(result["loudness_lufs"], float)
    assert isinstance(result["true_peak_dbtp"], float)
    assert result["loudness_lufs"] < 0  # LUFS is typically negative


def test_measure_loudness_nonexistent_file():
    """Verify measure_loudness raises ValueError for missing file."""
    from ai_radio.audio import measure_loudness

    with pytest.raises(ValueError, match="File not found"):
        measure_loudness(Path("/nonexistent/file.mp3"))


def test_measure_loudness_invalid_audio(tmp_path):
    """Verify measure_loudness raises ValueError for invalid audio."""
    from ai_radio.audio import measure_loudness

    invalid_file = tmp_path / "invalid.mp3"
    invalid_file.write_text("not an audio file")

    with pytest.raises(ValueError, match="Failed to measure loudness"):
        measure_loudness(invalid_file)
