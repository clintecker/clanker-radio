"""Play history tracking for AI Radio Station."""

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def record_play(
    db_path: Path,
    asset_id: str,
    source: str = "music"
) -> bool:
    """Record that an asset was played.

    Args:
        db_path: Database path
        asset_id: Asset ID
        source: Play source (music|override|break|bumper)

    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc)
        played_at = now.isoformat()

        # Calculate hour_bucket (SOW Section 6 requirement)
        hour_bucket = now.replace(
            minute=0,
            second=0,
            microsecond=0
        ).isoformat()

        cursor.execute(
            """
            INSERT INTO play_history (asset_id, played_at, source, hour_bucket)
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, played_at, source, hour_bucket)
        )

        conn.commit()
        conn.close()

        logger.info(f"Recorded play: {asset_id} from {source}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Failed to record play: {e}")
        return False


def get_recently_played_ids(
    db_path: Path,
    source: str = "music",
    hours: int = 24,
    limit: int = 50
) -> list[str]:
    """Get recently played asset IDs.

    Args:
        db_path: Database path
        source: Play source to query (music|override|break|bumper)
        hours: Look back this many hours
        limit: Maximum IDs to return

    Returns:
        List of asset IDs (most recent first)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        cursor.execute(
            """
            SELECT DISTINCT asset_id
            FROM play_history
            WHERE source = ?
              AND played_at >= ?
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (source, cutoff, limit)
        )

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Failed to get recent plays: {e}")
        return []
