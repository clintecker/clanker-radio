"""Database operations for asset management."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def insert_asset(
    conn: sqlite3.Connection,
    asset_id: str,
    path: Path,
    kind: str,
    duration_sec: float,
    loudness_lufs: Optional[float] = None,
    true_peak_dbtp: Optional[float] = None,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    energy_level: Optional[int] = None,
) -> None:
    """Insert asset record into database.

    Args:
        conn: SQLite database connection
        asset_id: SHA256 hash of file
        path: File path
        kind: Asset kind (music, break, bed, safety)
        duration_sec: Duration in seconds
        loudness_lufs: Integrated loudness in LUFS
        true_peak_dbtp: True peak in dBTP
        title: Track title
        artist: Artist name
        album: Album name
        energy_level: Energy level (0-100)

    Raises:
        ValueError: If asset with same path already exists
        sqlite3.IntegrityError: If database constraints violated
    """
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO assets (
                id, path, kind, duration_sec, loudness_lufs, true_peak_dbtp,
                energy_level, title, artist, album, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                str(path),
                kind,
                duration_sec,
                loudness_lufs,
                true_peak_dbtp,
                energy_level,
                title,
                artist,
                album,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: assets.path" in str(e):
            raise ValueError(f"Asset already exists at path: {path}") from e
        raise


def get_asset(conn: sqlite3.Connection, asset_id: str) -> Optional[dict]:
    """Retrieve asset record by ID.

    Args:
        conn: SQLite database connection
        asset_id: SHA256 hash of file

    Returns:
        Asset record as dict, or None if not found
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, path, kind, duration_sec, loudness_lufs, true_peak_dbtp,
               energy_level, title, artist, album, created_at
        FROM assets WHERE id = ?
        """,
        (asset_id,),
    )

    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "path": row[1],
        "kind": row[2],
        "duration_sec": row[3],
        "loudness_lufs": row[4],
        "true_peak_dbtp": row[5],
        "energy_level": row[6],
        "title": row[7],
        "artist": row[8],
        "album": row[9],
        "created_at": row[10],
    }


def get_asset_by_path(conn: sqlite3.Connection, path: Path) -> Optional[dict]:
    """Retrieve asset record by file path.

    Args:
        conn: SQLite database connection
        path: File path

    Returns:
        Asset record as dict, or None if not found
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, path, kind, duration_sec, loudness_lufs, true_peak_dbtp,
               energy_level, title, artist, album, created_at
        FROM assets WHERE path = ?
        """,
        (str(path),),
    )

    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "path": row[1],
        "kind": row[2],
        "duration_sec": row[3],
        "loudness_lufs": row[4],
        "true_peak_dbtp": row[5],
        "energy_level": row[6],
        "title": row[7],
        "artist": row[8],
        "album": row[9],
        "created_at": row[10],
    }
