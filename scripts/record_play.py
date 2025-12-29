#!/usr/bin/env python3
"""AI Radio Station - Record Play CLI.

Called by Liquidsoap on track transitions to log plays to the database.
Triggers immediate now_playing.json export for real-time frontend updates.
"""

import logging
import os
import subprocess
import sys
import time
import traceback
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

        # Write trigger marker for debugging
        marker = f"/tmp/export_triggered_{ts}.marker"
        Path(marker).touch()

        # Start in background with proper logging and environment
        with open(stdout_log, "w") as f_out, open(stderr_log, "w") as f_err:
            subprocess.Popen(
                [venv_python, export_script],
                stdout=f_out,
                stderr=f_err,
                start_new_session=True,
                cwd="/srv/ai_radio",
                env=export_env,
            )

        logger.info(f"Triggered export. Logs: {stdout_log} {stderr_log}")

    except Exception as e:
        # Add traceback for better context on Popen failures
        logger.warning(
            f"Failed to trigger export: {e}\n{traceback.format_exc()}"
        )


def main():
    """Entry point for script."""
    if len(sys.argv) < 2:
        logger.error("Usage: record_play.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    # Look up asset by path to get SHA256 ID
    import sqlite3
    from datetime import datetime, timezone

    conn = sqlite3.connect(config.paths.db_path)
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
