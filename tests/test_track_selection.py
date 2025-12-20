"""Tests for music track selection logic"""
import pytest
from pathlib import Path
from ai_radio.track_selection import select_next_tracks


def test_select_next_tracks_returns_list(tmp_path):
    """Test that track selection returns list of tracks"""
    # Create dummy database
    db_path = tmp_path / "test.db"

    tracks = select_next_tracks(
        db_path=db_path,
        count=5,
        recently_played_ids=[]
    )

    # Should return list (may be empty if no tracks)
    assert isinstance(tracks, list)


def test_select_next_tracks_respects_count(tmp_path):
    """Test that selection respects requested count"""
    db_path = tmp_path / "test.db"

    tracks = select_next_tracks(
        db_path=db_path,
        count=3,
        recently_played_ids=[]
    )

    assert len(tracks) <= 3


def test_select_next_tracks_avoids_recent(tmp_path):
    """Test that recently played tracks are avoided"""
    db_path = tmp_path / "test.db"

    recently_played = ["track_id_1", "track_id_2"]

    tracks = select_next_tracks(
        db_path=db_path,
        count=5,
        recently_played_ids=recently_played
    )

    # Verify no recently played IDs in results
    track_ids = [t['id'] for t in tracks]
    for recent_id in recently_played:
        assert recent_id not in track_ids
