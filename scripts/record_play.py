#!/usr/bin/env python3
"""AI Radio Station - Record Play CLI.

Called by Liquidsoap on track transitions to log plays to the database.
Triggers immediate now_playing.json export for real-time frontend updates.
"""

# DIAGNOSTIC: Write immediately before any imports
from pathlib import Path
import sys
import time

# Ensure log directory exists
log_dir = Path("/tmp/ai_radio_logs")
log_dir.mkdir(exist_ok=True)

with open(log_dir / "record_play_called.txt", "a") as f:
    f.write(f"{time.time()} - Called with: {sys.argv}\n")
    f.flush()

import logging
import os
import subprocess
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# CRITICAL: Change to project root so Pydantic can find .env file
project_root = Path(__file__).parent.parent
os.chdir(project_root)

from ai_radio.config import config

# Configure file-based logging to bypass stdio buffering from daemon
log_dir = Path("/tmp/ai_radio_logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "record_play.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - PID:%(process)d - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def trigger_export():
    """Export now_playing.json and notify SSE daemon.

    Calls export function directly (no subprocess spawning).
    Fast enough (<100ms) to not block Liquidsoap callback.
    Failures are logged but don't affect play logging.
    """
    try:
        # Import and call export function directly
        import sys
        sys.path.insert(0, "/srv/ai_radio/scripts")
        from export_now_playing import export_now_playing

        logger.info("Calling export_now_playing()...")
        success = export_now_playing()

        if success:
            logger.info("Export and SSE notification completed successfully")
        else:
            logger.warning("Export function returned False")

    except Exception:
        # Use logger.exception for full traceback
        logger.exception("Failed to export now_playing")


def main():
    """Entry point for script."""
    try:
        if len(sys.argv) < 2:
            logger.error("Usage: record_play.py <file_path>")
            sys.exit(1)

        file_path = sys.argv[1]
        logger.info(f"Processing file: {file_path}")

        # Look up asset by path to get SHA256 ID
        import sqlite3
        from datetime import datetime, timezone

        conn = sqlite3.connect(config.paths.db_path)
        logger.info("DB connection created")
        cursor = conn.cursor()

        cursor.execute("SELECT id, kind FROM assets WHERE path = ?", (file_path,))
        row = cursor.fetchone()

        if not row:
            logger.error(f"Asset not found in database: {file_path}")
            logger.error("Make sure all assets are ingested before playback")
            conn.close()
            sys.exit(1)

        asset_id, asset_kind = row
        logger.info(f"Found asset: {asset_id[:16]}... kind={asset_kind}")

        # Write to play_history with SHA256 ID
        now = datetime.now(timezone.utc)
        played_at = now.isoformat()
        hour_bucket = now.replace(minute=0, second=0, microsecond=0).isoformat()

        cursor.execute(
            "INSERT INTO play_history (asset_id, source, played_at, hour_bucket) VALUES (?, ?, ?, ?)",
            (asset_id, asset_kind, played_at, hour_bucket)
        )
        logger.info("Play history INSERT executed")
        conn.commit()
        logger.info("DB commit successful")
        conn.close()
        logger.info("DB connection closed")

        logger.info(f"Recorded play: {asset_id[:16]}... (kind={asset_kind})")

        # Trigger immediate now_playing.json export
        logger.info("Calling trigger_export()...")
        trigger_export()
        logger.info("Returned from trigger_export()")
        sys.exit(0)

    except Exception:
        logger.exception("An unhandled exception occurred in main()")
        sys.exit(1)
    finally:
        logger.info("--- main() function finished ---")


if __name__ == "__main__":
    logger.info(f"--- Script start. ARGV: {sys.argv} ---")
    main()
