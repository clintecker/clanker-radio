"""Tests for music track selection logic"""
import sqlite3
import pytest
from pathlib import Path
from ai_radio.track_selection import select_next_tracks, build_energy_flow


@pytest.fixture
def test_db(tmp_path):
    """Create test database with sample music tracks"""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create assets table
    cursor.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            energy_level INTEGER,
            duration_sec INTEGER,
            kind TEXT
        )
    """)

    # Insert test tracks with various energy levels
    test_tracks = [
        ("track_1", "/music/high1.mp3", "High Energy 1", "Artist A", "Album 1", 8, 180, "music"),
        ("track_2", "/music/high2.mp3", "High Energy 2", "Artist B", "Album 2", 9, 200, "music"),
        ("track_3", "/music/med1.mp3", "Medium Energy 1", "Artist C", "Album 3", 5, 190, "music"),
        ("track_4", "/music/med2.mp3", "Medium Energy 2", "Artist D", "Album 4", 4, 210, "music"),
        ("track_5", "/music/low1.mp3", "Low Energy 1", "Artist E", "Album 5", 2, 170, "music"),
        ("track_6", "/music/low2.mp3", "Low Energy 2", "Artist F", "Album 6", 3, 180, "music"),
        ("track_7", "/music/break.mp3", "Station Break", "Station", "Breaks", 5, 60, "break"),
    ]

    cursor.executemany(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        test_tracks
    )

    conn.commit()
    conn.close()

    return db_path


def test_select_next_tracks_returns_list(test_db):
    """Test that track selection returns list of tracks"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=5,
        recently_played_ids=[]
    )

    assert isinstance(tracks, list)
    assert len(tracks) > 0  # Should have tracks now


def test_select_next_tracks_respects_count(test_db):
    """Test that selection respects requested count"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=3,
        recently_played_ids=[]
    )

    assert len(tracks) <= 3


def test_select_next_tracks_avoids_recent(test_db):
    """Test that recently played tracks are avoided"""
    recently_played = ["track_1", "track_2"]

    tracks = select_next_tracks(
        db_path=test_db,
        count=5,
        recently_played_ids=recently_played
    )

    # Verify no recently played IDs in results
    track_ids = [t['id'] for t in tracks]
    for recent_id in recently_played:
        assert recent_id not in track_ids


def test_select_next_tracks_high_energy_filter(test_db):
    """Test high energy track filtering"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=10,
        recently_played_ids=[],
        energy_preference="high"
    )

    # All tracks should have energy_level >= 7
    for track in tracks:
        assert track['energy_level'] >= 7


def test_select_next_tracks_medium_energy_filter(test_db):
    """Test medium energy track filtering"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=10,
        recently_played_ids=[],
        energy_preference="medium"
    )

    # All tracks should have 4 <= energy_level <= 6
    for track in tracks:
        assert 4 <= track['energy_level'] <= 6


def test_select_next_tracks_low_energy_filter(test_db):
    """Test low energy track filtering"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=10,
        recently_played_ids=[],
        energy_preference="low"
    )

    # All tracks should have energy_level <= 3
    for track in tracks:
        assert track['energy_level'] <= 3


def test_select_next_tracks_only_music(test_db):
    """Test that only music tracks are selected, not breaks"""
    tracks = select_next_tracks(
        db_path=test_db,
        count=10,
        recently_played_ids=[]
    )

    # Should not include break tracks
    track_ids = [t['id'] for t in tracks]
    assert "track_7" not in track_ids  # track_7 is a break


def test_build_energy_flow_wave_pattern():
    """Test wave energy flow pattern"""
    flow = build_energy_flow(track_count=8, pattern="wave")

    assert len(flow) == 8
    # Wave pattern: medium, high, medium, low, repeat
    assert flow[:4] == ["medium", "high", "medium", "low"]
    assert flow[4:8] == ["medium", "high", "medium", "low"]


def test_build_energy_flow_ascending_pattern():
    """Test ascending energy flow pattern"""
    flow = build_energy_flow(track_count=6, pattern="ascending")

    assert len(flow) == 6
    # Ascending: low, medium, high, repeat
    assert flow[:3] == ["low", "medium", "high"]
    assert flow[3:6] == ["low", "medium", "high"]


def test_build_energy_flow_descending_pattern():
    """Test descending energy flow pattern"""
    flow = build_energy_flow(track_count=6, pattern="descending")

    assert len(flow) == 6
    # Descending: high, medium, low, repeat
    assert flow[:3] == ["high", "medium", "low"]
    assert flow[3:6] == ["high", "medium", "low"]


def test_build_energy_flow_mixed_pattern():
    """Test mixed (random) energy flow pattern"""
    flow = build_energy_flow(track_count=10, pattern="mixed")

    assert len(flow) == 10
    # All entries should be valid energy levels
    for energy in flow:
        assert energy in ["low", "medium", "high"]


def test_select_next_tracks_with_connection(test_db):
    """Test that passing connection parameter works correctly"""
    conn = sqlite3.connect(test_db)

    tracks1 = select_next_tracks(
        db_path=test_db,
        count=2,
        recently_played_ids=[],
        conn=conn
    )

    tracks2 = select_next_tracks(
        db_path=test_db,
        count=2,
        recently_played_ids=[],
        conn=conn
    )

    conn.close()

    # Both should return valid results
    assert len(tracks1) > 0
    assert len(tracks2) > 0
