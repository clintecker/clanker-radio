"""Tests for audio ingestion pipeline."""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

from ai_radio.ingest import ingest_audio_file


@pytest.fixture
def db_conn():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create assets table with same schema as production
    cursor.execute(
        """
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX idx_assets_path_unique ON assets(path)"
    )
    conn.commit()

    yield conn
    conn.close()


def test_ingest_audio_file_complete_pipeline(tmp_path):
    """Test complete ingestion pipeline with real test track."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    # Use temporary database and output directory
    db_path = tmp_path / "test.db"
    music_dir = tmp_path / "music"
    music_dir.mkdir()

    # Initialize database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX idx_assets_path_unique ON assets(path)"
    )
    conn.commit()
    conn.close()

    # Run ingestion
    result = ingest_audio_file(
        source_path=test_file,
        kind="music",
        db_path=db_path,
        music_dir=music_dir,
    )

    # Verify result
    assert result["id"] is not None
    assert len(result["id"]) == 64  # SHA256
    assert result["path"] == str(test_file)
    assert result["kind"] == "music"
    assert result["title"] == "Test Tone 440Hz"
    assert result["artist"] == "Test Artist"
    assert result["duration_sec"] > 29.0

    # Verify normalized file was created
    output_path = Path(result["output_path"])
    assert output_path.exists()
    assert output_path.parent == music_dir

    # Verify database record
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assets")
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT * FROM assets WHERE id = ?", (result["id"],))
    row = cursor.fetchone()
    assert row is not None
    conn.close()


def test_ingest_duplicate_file_detected(tmp_path):
    """Test that ingesting same file twice is detected."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    # Use temporary database and output directory
    db_path = tmp_path / "test.db"
    music_dir = tmp_path / "music"
    music_dir.mkdir()

    # Initialize database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX idx_assets_path_unique ON assets(path)"
    )
    conn.commit()
    conn.close()

    # First ingestion
    result1 = ingest_audio_file(
        source_path=test_file,
        kind="music",
        db_path=db_path,
        music_dir=music_dir,
    )

    # Second ingestion (should detect duplicate)
    result2 = ingest_audio_file(
        source_path=test_file,
        kind="music",
        db_path=db_path,
        music_dir=music_dir,
    )

    # Should return same asset
    assert result1["id"] == result2["id"]

    # Verify only one database record
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assets")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_ingest_nonexistent_file(tmp_path):
    """Test that nonexistent file raises ValueError."""
    db_path = tmp_path / "test.db"
    music_dir = tmp_path / "music"
    music_dir.mkdir()

    with pytest.raises(ValueError, match="Source file not found"):
        ingest_audio_file(
            source_path=Path("/nonexistent/file.mp3"),
            kind="music",
            db_path=db_path,
            music_dir=music_dir,
        )


def test_ingest_invalid_kind(tmp_path):
    """Test that invalid kind raises ValueError."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    db_path = tmp_path / "test.db"
    music_dir = tmp_path / "music"
    music_dir.mkdir()

    with pytest.raises(ValueError, match="Invalid kind"):
        ingest_audio_file(
            source_path=test_file,
            kind="invalid",
            db_path=db_path,
            music_dir=music_dir,
        )
