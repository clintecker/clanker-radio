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
    """Trigger export_now_playing.py in background (non-blocking).

    Export script has its own lock to prevent simultaneous runs.
    Runs async so we don't block Liquidsoap's on_track callback.
    Failures are logged but don't affect play logging.
    """
    try:
        # Use absolute paths
        export_script = "/srv/ai_radio/scripts/export_now_playing.py"
        venv_python = "/srv/ai_radio/.venv/bin/python"

        # Create log directory for diagnostic output
        log_dir = Path("/tmp/ai_radio_logs")
        log_dir.mkdir(exist_ok=True)
        ts = int(time.time())
        stdout_log = log_dir / f"export_{ts}.out"
        stderr_log = log_dir / f"export_{ts}.err"

        # CRITICAL FIX: Copy environment and augment it, don't replace it
        export_env = os.environ.copy()

        # Safely prepend our src path to PYTHONPATH
        python_path = export_env.get("PYTHONPATH", "")
        src_path = "/srv/ai_radio/src"
        if src_path not in python_path.split(os.pathsep):
            export_env["PYTHONPATH"] = f"{src_path}{os.pathsep}{python_path}".strip(os.pathsep)

        # Write trigger marker for debugging - with comprehensive logging
        marker = f"/tmp/export_triggered_{ts}.marker"
        try:
            import pwd
            current_user = pwd.getpwuid(os.getuid()).pw_name
            logger.info(f"v2: Attempting to touch marker {marker} as user '{current_user}'")
            Path(marker).touch()
            logger.info(f"v2: Successfully touched marker {marker}")
        except Exception as e:
            logger.error(f"v2: FAILED to create marker {marker}. Error: {e}", exc_info=True)

        # Start in background with proper logging and environment
        # Note: Don't use 'with' context manager - it closes file handles
        # before subprocess can use them. Open files and let subprocess inherit them.
        f_out = open(stdout_log, "w")
        f_err = open(stderr_log, "w")
        subprocess.Popen(
            [venv_python, export_script],
            stdout=f_out,
            stderr=f_err,
            start_new_session=True,
            cwd="/srv/ai_radio",
            env=export_env,
            close_fds=False,  # Keep file descriptors open for subprocess
        )

        logger.info(f"v2: Triggered export. Logs: {stdout_log} {stderr_log}")

    except Exception:
        # Use logger.exception for full traceback
        logger.exception("Failed to trigger export")


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
