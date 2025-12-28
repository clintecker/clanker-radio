"""Tests for database asset operations."""

import pytest
import sqlite3
from pathlib import Path

from ai_radio.db_assets import insert_asset, get_asset, get_asset_by_id, get_asset_by_path


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


def test_insert_asset(db_conn):
    """Test inserting asset into database."""
    insert_asset(
        db_conn,
        asset_id="abc123",
        path=Path("/test/track.mp3"),
        kind="music",
        duration_sec=180.0,
        loudness_lufs=-18.5,
        true_peak_dbtp=-1.2,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        energy_level=75,
    )

    # Verify asset was inserted
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM assets")
    assert cursor.fetchone()[0] == 1


def test_insert_duplicate_path_raises_error(db_conn):
    """Test that inserting duplicate path raises ValueError."""
    insert_asset(
        db_conn,
        asset_id="abc123",
        path=Path("/test/track.mp3"),
        kind="music",
        duration_sec=180.0,
    )

    # Try to insert another asset with same path
    with pytest.raises(ValueError, match="Asset already exists at path"):
        insert_asset(
            db_conn,
            asset_id="def456",
            path=Path("/test/track.mp3"),
            kind="music",
            duration_sec=200.0,
        )


def test_get_asset_by_id(db_conn):
    """Test retrieving asset by ID."""
    insert_asset(
        db_conn,
        asset_id="abc123",
        path=Path("/test/track.mp3"),
        kind="music",
        duration_sec=180.0,
        loudness_lufs=-18.5,
        true_peak_dbtp=-1.2,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        energy_level=75,
    )

    asset = get_asset_by_id(db_conn, "abc123")

    assert asset is not None
    assert asset["id"] == "abc123"
    assert asset["path"] == "/test/track.mp3"
    assert asset["kind"] == "music"
    assert asset["duration_sec"] == 180.0
    assert asset["loudness_lufs"] == -18.5
    assert asset["true_peak_dbtp"] == -1.2
    assert asset["title"] == "Test Track"
    assert asset["artist"] == "Test Artist"
    assert asset["album"] == "Test Album"
    assert asset["energy_level"] == 75
    assert "created_at" in asset


def test_get_asset_not_found(db_conn):
    """Test that get_asset returns None for nonexistent ID."""
    asset = get_asset(db_conn, "nonexistent")
    assert asset is None


def test_get_asset_by_path(db_conn):
    """Test retrieving asset by file path."""
    insert_asset(
        db_conn,
        asset_id="abc123",
        path=Path("/test/track.mp3"),
        kind="music",
        duration_sec=180.0,
        title="Test Track",
    )

    asset = get_asset_by_path(db_conn, Path("/test/track.mp3"))

    assert asset is not None
    assert asset["id"] == "abc123"
    assert asset["path"] == "/test/track.mp3"


def test_get_asset_by_path_not_found(db_conn):
    """Test that get_asset_by_path returns None for nonexistent path."""
    asset = get_asset_by_path(db_conn, Path("/nonexistent/track.mp3"))
    assert asset is None


def test_insert_asset_with_minimal_fields(db_conn):
    """Test inserting asset with only required fields."""
    insert_asset(
        db_conn,
        asset_id="abc123",
        path=Path("/test/track.mp3"),
        kind="music",
        duration_sec=180.0,
    )

    asset = get_asset(db_conn, "abc123")

    assert asset is not None
    assert asset["loudness_lufs"] is None
    assert asset["true_peak_dbtp"] is None
    assert asset["title"] is None
    assert asset["artist"] is None
    assert asset["album"] is None
    assert asset["energy_level"] is None
