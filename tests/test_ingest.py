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
    test_file = Path("tests/fixtures/test_track.mp3")

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
        output_dir=music_dir,
    )

    # Verify result
    assert result["id"] is not None
    assert len(result["id"]) == 64  # SHA256
    assert result["source_path"] == str(test_file)
    assert result["kind"] == "music"
    # Note: test fixture is minimal so title/artist/duration will be defaults
    assert result["duration_sec"] > 0

    # Verify normalized file was created
    output_path = Path(result["path"])
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
    test_file = Path("tests/fixtures/test_track.mp3")

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
        output_dir=music_dir,
    )

    # Second ingestion (should detect duplicate)
    result2 = ingest_audio_file(
        source_path=test_file,
        kind="music",
        db_path=db_path,
        output_dir=music_dir,
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
            output_dir=music_dir,
        )


def test_ingest_invalid_kind(tmp_path):
    """Test that invalid kind raises ValueError."""
    test_file = Path("tests/fixtures/test_track.mp3")

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
            output_dir=music_dir,
        )


def test_ingest_same_content_different_paths_deduplicates(tmp_path):
    """Verify that files with same content but different paths deduplicate."""
    import shutil

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

    # Create two copies of same file with different names
    test_track = Path("tests/fixtures/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    copy1 = tmp_path / "song1.mp3"
    copy2 = tmp_path / "song2.mp3"
    shutil.copy(test_track, copy1)
    shutil.copy(test_track, copy2)

    # Ingest first copy
    result1 = ingest_audio_file(copy1, "music", db_path, output_dir=music_dir)

    # Ingest second copy - should return same asset
    result2 = ingest_audio_file(copy2, "music", db_path, output_dir=music_dir)

    # Both should have same asset ID (based on SHA256 content)
    assert result1["id"] == result2["id"]

    # Should only create one normalized file
    assert (music_dir / f"{result1['id']}.mp3").exists()
    assert len(list(music_dir.glob("*.mp3"))) == 1


def test_ingest_existing_registers_without_normalization(tmp_path):
    """Verify ingest_existing=True skips normalization."""
    import shutil
    from ai_radio.ingest import ingest_audio_file

    test_track = Path("tests/fixtures/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    # Copy to temp location
    source_file = tmp_path / "existing.mp3"
    shutil.copy(test_track, source_file)

    # Set up database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety', 'bumper')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER,
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # Ingest with ingest_existing=True
    result = ingest_audio_file(
        source_path=source_file,
        kind="bumper",
        db_path=db_path,
        ingest_existing=True,
    )

    # Should use source path as-is
    assert result["path"] == str(source_file)
    assert result["kind"] == "bumper"
    assert result["loudness_lufs"] is not None  # Still measured
    assert result["duration_sec"] > 0


def test_ingest_existing_requires_no_output_dir():
    """Verify ingest_existing=True doesn't require output_dir."""
    from ai_radio.ingest import ingest_audio_file

    # This should NOT raise even though output_dir not provided
    # (Will fail at file exists check, but signature should work)
    try:
        ingest_audio_file(
            source_path=Path("/nonexistent.mp3"),
            kind="bumper",
            db_path=Path("/tmp/test.db"),
            ingest_existing=True,
        )
    except ValueError as e:
        # Should fail on file not found, not missing output_dir
        assert "not found" in str(e).lower()
        assert "output_dir" not in str(e).lower()


def test_ingest_new_requires_output_dir():
    """Verify ingest_existing=False requires output_dir."""
    from ai_radio.ingest import ingest_audio_file

    with pytest.raises(ValueError, match="output_dir.*required"):
        ingest_audio_file(
            source_path=Path("/nonexistent.mp3"),
            kind="music",
            db_path=Path("/tmp/test.db"),
            ingest_existing=False,
        )
