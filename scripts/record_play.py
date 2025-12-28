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
        logger.error("Usage: record_play.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    # Look up asset by path to get SHA256 ID
    import sqlite3
    from datetime import datetime, timezone

    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, kind FROM assets WHERE path = ?", (file_path,))
    row = cursor.fetchone()

    if not row:
        logger.error(f"Asset not found in database: {file_path}")
        logger.error("Make sure all assets are ingested before playback")
        conn.close()
        sys.exit(1)

    asset_id, asset_kind = row

    # Write to play_history with SHA256 ID
    now = datetime.now(timezone.utc)
    played_at = now.isoformat()
    hour_bucket = now.replace(minute=0, second=0, microsecond=0).isoformat()

    cursor.execute(
        "INSERT INTO play_history (asset_id, source, played_at, hour_bucket) VALUES (?, ?, ?, ?)",
        (asset_id, asset_kind, played_at, hour_bucket)
    )
    conn.commit()
    conn.close()

    logger.info(f"Recorded play: {asset_id[:16]}... (kind={asset_kind})")

    # Trigger immediate now_playing.json export
    trigger_export()
    sys.exit(0)


if __name__ == "__main__":
    main()
