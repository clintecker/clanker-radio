"""Integration tests for export_now_playing.py, focusing on database queries."""

import sqlite3
import sys
import datetime as dt_module
from pathlib import Path

import pytest

# Add scripts directory to path so we can import export_now_playing
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Module to be tested
import export_now_playing


@pytest.fixture(autouse=True)
def mock_config(mocker):
    """Mock the global config object to ensure test isolation."""
    mock_cfg = mocker.MagicMock()
    mock_cfg.station_name = "Test Radio"
    mock_cfg.db_path = ":memory:"  # Use in-memory database
    mocker.patch("export_now_playing.config", mock_cfg)
    return mock_cfg


@pytest.fixture
def db_connection():
    """Pytest fixture for an in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create schema matching the application's database
    cursor.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            title TEXT,
            artist TEXT,
            album TEXT,
            duration_sec REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            played_at TEXT NOT NULL,
            source TEXT NOT NULL
        )
    """)
    conn.commit()
    yield conn
    conn.close()


def test_get_current_playing_for_music_track(db_connection, mocker):
    """
    Music track in assets should match via LEFT JOIN within 10 minutes.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_stream_info", return_value={})

    cursor = db_connection.cursor()
    # Insert a music track into assets
    cursor.execute(
        "INSERT INTO assets (id, path, kind, title, artist, album, duration_sec) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("song1_hash", "/path/to/music/song1.mp3", "music", "Test Song", "Test Artist", "Test Album", 180.5)
    )
    # Insert a corresponding play_history entry 5 minutes ago
    five_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=5)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("song1_hash", five_min_ago, "music")
    )
    db_connection.commit()

    # Mock sqlite3.connect to return our fixture connection
    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "song1_hash"
    assert current["title"] == "Test Song"
    assert current["artist"] == "Test Artist"
    assert current["played_at"] == five_min_ago
    assert current["source"] == "music"
    assert current["duration_sec"] == 180.5


def test_get_current_playing_no_recent_plays(db_connection, mocker):
    """
    No plays within 10 minutes should return None.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_stream_info", return_value={})

    cursor = db_connection.cursor()
    # Insert a play_history entry 15 minutes ago (outside 10-minute window)
    fifteen_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=15)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("song1_hash", fifteen_min_ago, "music")
    )
    db_connection.commit()

    # Mock sqlite3.connect to return our fixture connection
    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is None


def test_get_current_playing_deleted_asset(db_connection, mocker):
    """
    Deleted asset (play_history exists but assets record missing) should show [Deleted Track].
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_stream_info", return_value={})

    cursor = db_connection.cursor()
    # Insert a play_history entry but NO corresponding assets entry
    five_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=5)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("deleted_hash", five_min_ago, "music")
    )
    db_connection.commit()

    # Mock sqlite3.connect to return our fixture connection
    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "deleted_hash"
    assert current["title"] == "[Deleted Track]"
    assert current["artist"] == "Unknown"
    assert current["duration_sec"] == 0
    assert current["played_at"] == five_min_ago


def test_get_current_playing_most_recent(db_connection, mocker):
    """
    Multiple plays should return the most recent one.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_stream_info", return_value={})

    cursor = db_connection.cursor()
    # Insert two tracks
    cursor.execute(
        "INSERT INTO assets (id, path, kind, title, artist, album, duration_sec) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("song1_hash", "/path/to/song1.mp3", "music", "Song 1", "Artist 1", "Album 1", 180.5)
    )
    cursor.execute(
        "INSERT INTO assets (id, path, kind, title, artist, album, duration_sec) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("song2_hash", "/path/to/song2.mp3", "music", "Song 2", "Artist 2", "Album 2", 200.0)
    )

    # Insert two play_history entries
    five_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=5)).isoformat()
    two_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=2)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("song1_hash", five_min_ago, "music")
    )
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("song2_hash", two_min_ago, "music")
    )
    db_connection.commit()

    # Mock sqlite3.connect to return our fixture connection
    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "song2_hash"  # Most recent
    assert current["title"] == "Song 2"
    assert current["played_at"] == two_min_ago
