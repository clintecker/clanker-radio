#!/usr/bin/env python3
"""
AI Radio Station - Music Enqueue Service
Maintains music queue depth by selecting and pushing tracks to Liquidsoap
"""
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.liquidsoap_client import LiquidsoapClient
from ai_radio.track_selection import select_next_tracks, build_energy_flow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
QUEUE_NAME = "music"
MIN_QUEUE_DEPTH = 2  # Minimum tracks in queue
TARGET_QUEUE_DEPTH = 5  # Fill to this level
RECENT_HISTORY_SIZE = 20  # Track last N played to avoid repetition (reduced from 50 for small library)


def get_recently_played_ids(db_path: Path, count: int = RECENT_HISTORY_SIZE) -> list[str]:
    """
    Get IDs of recently played tracks from play_history table

    Note: Phase 6 implements the writing to play_history.
    Phase 5 must be able to read it (even if empty initially).

    Args:
        db_path: Database path
        count: Number of recent IDs to fetch

    Returns:
        List of track IDs
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Fetch last N asset_ids from play_history (SOW Section 6)
            cursor.execute(
                """
                SELECT asset_id
                FROM play_history
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (count,)
            )

            ids = [row[0] for row in cursor.fetchall()]

        logger.info(f"Loaded {len(ids)} recently played IDs for anti-repetition")
        return ids

    except sqlite3.Error as e:
        logger.warning(f"Failed to fetch play history: {e}")
        return []  # Graceful degradation
    except Exception as e:
        logger.error(f"Unexpected error fetching history: {e}")
        return []


def main():
    """Main entry point"""
    client = LiquidsoapClient()

    # Check current queue depth
    logger.info(f"Checking {QUEUE_NAME} queue depth...")

    try:
        current_depth = client.get_queue_length(QUEUE_NAME)

        if current_depth < 0:
            logger.error("Failed to get queue depth - Liquidsoap not running?")
            sys.exit(1)

        logger.info(f"Current queue depth: {current_depth}")

        if current_depth >= MIN_QUEUE_DEPTH:
            logger.info(f"Queue depth sufficient ({current_depth} >= {MIN_QUEUE_DEPTH})")
            sys.exit(0)

        # Queue needs filling
        tracks_needed = TARGET_QUEUE_DEPTH - current_depth
        logger.info(f"Need to add {tracks_needed} tracks")

        # Get recently played IDs (for anti-repetition)
        recently_played = get_recently_played_ids(config.db_path)

        # Select tracks randomly without energy filtering
        all_tracks = select_next_tracks(
            db_path=config.db_path,
            count=tracks_needed,
            recently_played_ids=recently_played,
            energy_preference=None  # No energy filtering
        )

        if not all_tracks:
            logger.error("No tracks available to enqueue")
            sys.exit(1)

        # Push tracks to Liquidsoap
        success_count = 0
        for track in all_tracks:
            # Validate file exists before pushing
            track_path = Path(track['path'])
            if not track_path.exists():
                logger.warning(f"  - Skipping non-existent track: {track_path}")
                continue

            if client.push_track(QUEUE_NAME, str(track_path)):
                success_count += 1
                logger.info(f"  ✓ Enqueued: {track.get('title', 'Unknown')} by {track.get('artist', 'Unknown')}")
            else:
                logger.error(f"  ✗ Failed to enqueue: {track_path}")

        logger.info(f"Enqueued {success_count}/{len(all_tracks)} tracks")

        if success_count > 0:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Enqueue service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
