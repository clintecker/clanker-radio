#!/usr/bin/env python3
"""Generate a JSON index of recent news breaks for the public API.

Scans the breaks directory for break_*.mp3 files from the last 24 hours
(by filename timestamp) and writes an index.json with metadata.

Output format:
{
    "generated_at": "2026-03-03T10:00:00Z",
    "count": 24,
    "breaks": [
        {
            "filename": "break_20260303_095118.mp3",
            "timestamp": "2026-03-03T09:51:18",
            "url": "/api/breaks/break_20260303_095118.mp3",
            "size_bytes": 234567
        },
        ...
    ]
}

Run after each break generation (ExecStartPost) or via cron.
"""

import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

FILENAME_RE = re.compile(r"^break_(\d{8})_(\d{6})\.mp3$")
INDEX_FILENAME = "index.json"
LOOKBACK_HOURS = 24


def parse_break_timestamp(filename: str) -> datetime | None:
    """Extract datetime from a break filename like break_20260303_095118.mp3."""
    match = FILENAME_RE.match(filename)
    if not match:
        return None
    return datetime.strptime(f"{match.group(1)}{match.group(2)}", "%Y%m%d%H%M%S")


def generate_index() -> bool:
    """Scan breaks directory and write index.json with last 24h of breaks."""
    breaks_dir = config.paths.breaks_path

    if not breaks_dir.exists():
        logger.error(f"Breaks directory not found: {breaks_dir}")
        return False

    cutoff = datetime.now() - timedelta(hours=LOOKBACK_HOURS)
    entries = []

    for path in breaks_dir.glob("break_*.mp3"):
        if path.is_symlink():
            continue

        ts = parse_break_timestamp(path.name)
        if ts is None or ts < cutoff:
            continue

        entries.append(
            {
                "filename": path.name,
                "timestamp": ts.isoformat(),
                "url": f"/api/breaks/{path.name}",
                "size_bytes": path.stat().st_size,
            }
        )

    # Most recent first
    entries.sort(key=lambda e: e["timestamp"], reverse=True)

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "breaks": entries,
    }

    index_path = breaks_dir / INDEX_FILENAME
    index_path.write_text(json.dumps(index, indent=2))
    logger.info(f"Wrote {index_path} with {len(entries)} breaks")
    return True


def main():
    try:
        success = generate_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Failed to generate breaks index: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
