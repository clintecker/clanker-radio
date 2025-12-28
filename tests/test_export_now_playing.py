"""Integration tests for export_now_playing.py, focusing on database queries."""

import os
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
    Scenario 1: Music track in assets should match on a.path within 10 minutes.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_icecast_status", return_value={})
    mocker.patch(
        "export_now_playing.get_liquidsoap_metadata",
        return_value={"filename": "/path/to/music/song1.mp3"}
    )
    # This dependency is called as a fallback, ensure it doesn't return anything
    mocker.patch("export_now_playing.get_duration_from_file", return_value=None)

    cursor = db_connection.cursor()
    # Insert a music track into assets
    cursor.execute(
        "INSERT INTO assets (id, path, title, artist, album, duration_sec) VALUES (?, ?, ?, ?, ?, ?)",
        ("song1_hash", "/path/to/music/song1.mp3", "Test Song", "Test Artist", "Test Album", 180.5)
    )
    # Insert a corresponding play_history entry 5 minutes ago
    # Use real current time (unfrozen) because SQLite's datetime('now') is not affected by freezegun
    five_min_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(minutes=5)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("song1_hash", five_min_ago, "music")
    )
    db_connection.commit()

    # Link the in-memory DB to the function via DB_PATH patch
    mocker.patch("export_now_playing.DB_PATH", ":memory:")
    # We need to mock connect to return our fixture connection
    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "song1_hash"
    assert current["title"] == "Test Song"
    # SQL uses COALESCE(a.artist, ...) so it returns artist from assets when available
    assert current["artist"] == "Test Artist"
    assert current["played_at"] == five_min_ago
    assert current["source"] == "music"


def test_get_current_playing_for_station_id_recent(db_connection, mocker, mock_config):
    """
    Scenario 2: Station ID not in assets should match on ph.asset_id within 30s.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_icecast_status", return_value={})
    mocker.patch(
        "export_now_playing.get_liquidsoap_metadata",
        return_value={"filename": "/path/to/bumpers/station_id_5.mp3"}
    )
    mocker.patch("export_now_playing.get_duration_from_file", return_value=15.0)

    cursor = db_connection.cursor()
    # Insert a play_history entry 15 seconds ago for a bumper
    # Use real current time because SQLite's datetime('now') is not affected by freezegun
    fifteen_sec_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(seconds=15)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("station_id_5", fifteen_sec_ago, "bumper")
    )
    db_connection.commit()

    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "station_id_5"
    assert current["title"] == "Station Identification"
    assert current["artist"] == mock_config.station_name
    assert current["played_at"] == fifteen_sec_ago
    assert current["source"] == "bumper"
    assert current["duration_sec"] == 15.0


def test_get_current_playing_for_station_id_outside_30s_window(db_connection, mocker):
    """
    Scenario 3: Station ID play >30s ago should NOT match (30-second window enforcement).

    The 30-second time window should prevent matching old plays of the same asset_id.
    When the query rejects the old play, the code falls back to constructing metadata
    from the filename with a current timestamp.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_icecast_status", return_value={})
    mocker.patch(
        "export_now_playing.get_liquidsoap_metadata",
        return_value={"filename": "/path/to/bumpers/station_id_5.mp3"}
    )
    mocker.patch("export_now_playing.get_duration_from_file", return_value=15.0)

    cursor = db_connection.cursor()
    # Insert a play_history entry 45 seconds ago (outside 30-second window)
    forty_five_sec_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(seconds=45)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("station_id_5", forty_five_sec_ago, "bumper")
    )
    db_connection.commit()

    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    # The 30-second window should reject the old play, falling back to constructed metadata
    assert current is not None
    # Fallback doesn't populate asset_id from database
    assert current["asset_id"] is None
    assert current["title"] == "Station Identification"
    assert current["source"] == "bumper"
    # Verify fallback behavior: timestamp should be recent (not 45s ago)
    assert current["played_at"] != forty_five_sec_ago
    played_at_dt = dt_module.datetime.fromisoformat(current["played_at"].replace('Z', '+00:00'))
    now_dt = dt_module.datetime.now(dt_module.timezone.utc)
    time_diff = (now_dt - played_at_dt).total_seconds()
    assert time_diff < 2, f"Expected fallback timestamp to be recent, but it was {time_diff}s ago"


def test_get_current_playing_for_station_id_most_recent(db_connection, mocker):
    """
    Scenario 4: Multiple plays of same station ID, should return the most recent.
    """
    # --- Setup ---
    mocker.patch("export_now_playing.get_icecast_status", return_value={})
    mocker.patch(
        "export_now_playing.get_liquidsoap_metadata",
        return_value={"filename": "/path/to/bumpers/station_id_5.mp3"}
    )
    mocker.patch("export_now_playing.get_duration_from_file", return_value=15.0)

    cursor = db_connection.cursor()
    # Insert two play_history entries, one more recent than the other
    # Use real current time because SQLite's datetime('now') is not affected by freezegun
    twenty_sec_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(seconds=20)).isoformat()
    ten_sec_ago = (dt_module.datetime.now(dt_module.timezone.utc) - dt_module.timedelta(seconds=10)).isoformat()
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("station_id_5", twenty_sec_ago, "bumper")
    )
    cursor.execute(
        "INSERT INTO play_history (asset_id, played_at, source) VALUES (?, ?, ?)",
        ("station_id_5", ten_sec_ago, "bumper")
    )
    db_connection.commit()

    mocker.patch("sqlite3.connect", return_value=db_connection)

    # --- Execute ---
    current, _ = export_now_playing.get_current_playing()

    # --- Assert ---
    assert current is not None
    assert current["asset_id"] == "station_id_5"
    assert current["played_at"] == ten_sec_ago  # Verified it got the most recent one
