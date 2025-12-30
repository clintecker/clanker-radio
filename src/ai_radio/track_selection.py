"""
AI Radio Station - Track Selection Logic
Energy-aware music selection with anti-repetition rules
"""
import logging
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def select_next_tracks(
    db_path: Path,
    count: int = 10,
    recently_played_ids: list[str] | None = None,
    energy_preference: str | None = None,
    conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """
    Select next tracks from database using energy-aware logic

    Args:
        db_path: Path to SQLite database
        count: Number of tracks to select
        recently_played_ids: IDs to exclude (anti-repetition)
        energy_preference: "high", "medium", "low", or None for mixed
        conn: Optional existing database connection (for efficiency)

    Returns:
        List of track dictionaries with id, path, title, artist, energy_level
    """
    if recently_played_ids is None:
        recently_played_ids = []

    # Manage connection lifecycle
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(db_path)
        close_conn = True

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with exclusions
        placeholders = ','.join('?' * len(recently_played_ids))
        exclusion_clause = f"AND id NOT IN ({placeholders})" if recently_played_ids else ""

        # Energy preference filter
        if energy_preference == "high":
            energy_clause = "AND energy_level >= 7"
        elif energy_preference == "medium":
            energy_clause = "AND energy_level BETWEEN 4 AND 6"
        elif energy_preference == "low":
            energy_clause = "AND energy_level <= 3"
        else:
            energy_clause = ""  # Mixed energy

        # Time-based Malware Groove filtering (1 AM - 8 AM Chicago time only)
        from ai_radio.config import config
        now = datetime.now(ZoneInfo(config.station_tz))
        hour = now.hour

        # Exclude Malware Grooves outside of 1 AM - 8 AM window
        if hour < 1 or hour >= 8:
            malware_exclusion = "AND title NOT LIKE 'Malware Groove%'"
            logger.debug(f"Excluding Malware Grooves (current hour: {hour})")
        else:
            malware_exclusion = ""
            logger.debug(f"Allowing Malware Grooves (current hour: {hour})")

        query = f"""
            SELECT id, path, title, artist, album, energy_level, duration_sec
            FROM assets
            WHERE kind = 'music'
            {exclusion_clause}
            {energy_clause}
            {malware_exclusion}
            ORDER BY RANDOM()
            LIMIT ?
        """

        params = list(recently_played_ids) + [count]
        cursor.execute(query, params)

        rows = cursor.fetchall()

        tracks = [dict(row) for row in rows]
        logger.info(f"Selected {len(tracks)} tracks (energy: {energy_preference or 'mixed'})")

        return tracks

    except sqlite3.Error as e:
        logger.error(f"Database error selecting tracks: {e}")
        return []

    except Exception as e:
        logger.error(f"Unexpected error selecting tracks: {e}")
        return []

    finally:
        if close_conn:
            conn.close()


def build_energy_flow(
    track_count: int,
    pattern: str = "wave"
) -> list[str]:
    """
    Build energy flow pattern for track selection

    Args:
        track_count: Number of tracks in set
        pattern: Flow pattern - "wave", "ascending", "descending", "mixed"

    Returns:
        List of energy preferences in order (e.g., ["medium", "high", "low", ...])
    """
    if pattern == "wave":
        # Gradual build and release: medium → high → medium → low → medium
        cycle = ["medium", "high", "medium", "low"]
        return (cycle * (track_count // len(cycle) + 1))[:track_count]

    elif pattern == "ascending":
        # Build energy: low → medium → high, repeat
        cycle = ["low", "medium", "high"]
        return (cycle * (track_count // len(cycle) + 1))[:track_count]

    elif pattern == "descending":
        # Release energy: high → medium → low, repeat
        cycle = ["high", "medium", "low"]
        return (cycle * (track_count // len(cycle) + 1))[:track_count]

    else:  # mixed
        # Random energy levels
        energy_levels = ["low", "medium", "high"]
        return [random.choice(energy_levels) for _ in range(track_count)]
