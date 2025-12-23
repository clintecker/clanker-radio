#!/usr/bin/env python3
"""AI Radio Station - Record Play CLI.

Called by Liquidsoap on track transitions to log plays to the database.
Triggers immediate now_playing.json export for real-time frontend updates.
"""

import logging
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.play_history import record_play

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def trigger_export():
    """Trigger export_now_playing.py in background (non-blocking).

    Export script has its own lock to prevent simultaneous runs.
    Runs async so we don't block Liquidsoap's on_track callback.
    Failures are logged but don't affect play logging.
    """
    try:
        export_script = Path(__file__).parent / "export_now_playing.py"

        # Start in background with LOW priority (nice/ionice)
        # Export script will handle its own locking
        subprocess.Popen(
            ["nice", "-n", "15", "ionice", "-c", "3", sys.executable, str(export_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )

        logger.debug("Triggered now_playing.json export")
    except Exception as e:
        # Don't fail the play logging if export trigger fails
        logger.warning(f"Failed to trigger export: {e}")


def main():
    """Entry point for script."""
    if len(sys.argv) < 2:
        logger.error("Usage: record_play.py <file_path> [source]")
        sys.exit(1)

    file_path = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else "music"

    # Detect station IDs and override source type
    # Station IDs come through breaks queue but should be tagged as "bumper"
    if source == "break" and ("/bumpers/" in file_path or "station_id" in file_path):
        source = "bumper"
        logger.info(f"Detected station ID, changing source from 'break' to 'bumper'")

    # Look up asset by path to get its ID (sha256 hash)
    import sqlite3
    import subprocess
    from datetime import datetime, timezone
    try:
        conn = sqlite3.connect(config.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE path = ?", (file_path,))
        row = cursor.fetchone()

        if not row:
            # Asset not in database (breaks, bumpers, beds)
            # Use filename as asset_id for tracking
            asset_id = Path(file_path).stem  # e.g., "break_20251222_025240" or "station_id_11"

            # Duration should be calculated during ingestion, not here
            # Removed expensive ffprobe call that was causing CPU contention
            duration_sec = None

            # Record play directly to play_history (not in assets table)
            # Use Python datetime for consistent ISO format with timezone (matches music tracks)
            now = datetime.now(timezone.utc)
            played_at = now.isoformat()
            hour_bucket = now.replace(minute=0, second=0, microsecond=0).isoformat()

            cursor.execute(
                """INSERT INTO play_history (asset_id, played_at, source, hour_bucket)
                   VALUES (?, ?, ?, ?)""",
                (asset_id, played_at, source, hour_bucket)
            )
            conn.commit()
            conn.close()

            logger.info(f"Recorded non-asset play: {asset_id} ({source}) duration={duration_sec}s")

            # Trigger immediate now_playing.json export
            trigger_export()
            sys.exit(0)
        else:
            asset_id = row[0]
            conn.close()

    except Exception as e:
        logger.error(f"Failed to lookup/record asset: {e}")
        sys.exit(1)

    if record_play(config.db_path, asset_id, source):
        logger.info(f"Recorded play: {asset_id} from {source}")

        # Trigger immediate now_playing.json export
        trigger_export()
        sys.exit(0)
    else:
        logger.error(f"Failed to record play: {asset_id}")
        sys.exit(1)


if __name__ == "__main__":
    main()
