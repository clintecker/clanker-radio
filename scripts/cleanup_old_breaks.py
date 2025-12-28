#!/usr/bin/env python3
"""Cleanup old break assets.

Automatically removes break assets (news, weather) older than specified threshold.
Designed for daily cron execution to prevent accumulation of stale content.

Breaks are generated content that becomes outdated and should be removed:
- News breaks contain time-sensitive headlines
- Weather breaks contain current conditions that expire

Usage:
    ./scripts/cleanup_old_breaks.py [--age-hours HOURS] [--dry-run]

    --age-hours: Delete breaks older than this (default: 48)
    --dry-run: Show what would be deleted without actually deleting

Examples:
    # Delete breaks older than 48 hours (default)
    ./scripts/cleanup_old_breaks.py

    # Delete breaks older than 24 hours
    ./scripts/cleanup_old_breaks.py --age-hours 24

    # Preview what would be deleted
    ./scripts/cleanup_old_breaks.py --dry-run

Exit codes:
    0: Success (files deleted or dry-run completed)
    1: Error (database or filesystem issues)
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def cleanup_old_breaks(db_path: Path, age_hours: int, dry_run: bool) -> int:
    """Remove break assets older than specified age.

    Args:
        db_path: Path to SQLite database
        age_hours: Delete breaks older than this many hours
        dry_run: If True, show what would be deleted without deleting

    Returns:
        Number of breaks deleted (or would be deleted in dry-run mode)

    Raises:
        sqlite3.Error: If database operations fail
        OSError: If filesystem operations fail
    """
    # Calculate threshold timestamp
    threshold = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    threshold_iso = threshold.isoformat()

    logger.info(f"Cleanup threshold: {threshold_iso} ({age_hours} hours ago)")

    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    try:
        # Find breaks older than threshold
        cursor.execute(
            """
            SELECT id, path, created_at
            FROM assets
            WHERE kind = 'break' AND created_at < ?
            ORDER BY created_at ASC
            """,
            (threshold_iso,),
        )

        old_breaks = cursor.fetchall()

        if not old_breaks:
            logger.info("No old breaks found to clean up")
            return 0

        logger.info(f"Found {len(old_breaks)} old breaks to clean up")

        deleted_count = 0
        for asset_id, path_str, created_at in old_breaks:
            path = Path(path_str)

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would delete: {path.name} "
                    f"(id={asset_id[:8]}..., created={created_at})"
                )
                deleted_count += 1
            else:
                # Delete from database first
                try:
                    cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
                    conn.commit()
                    logger.info(
                        f"Deleted from database: {path.name} "
                        f"(id={asset_id[:8]}..., created={created_at})"
                    )
                except sqlite3.Error as e:
                    logger.error(
                        f"Failed to delete from database: {path.name} "
                        f"(id={asset_id[:8]}...) - {e}"
                    )
                    conn.rollback()
                    continue

                # Then delete file from filesystem
                try:
                    if path.exists():
                        path.unlink()
                        logger.info(f"Deleted file: {path}")
                        deleted_count += 1
                    else:
                        logger.warning(
                            f"File already missing (deleted elsewhere?): {path}"
                        )
                        deleted_count += 1
                except OSError as e:
                    logger.error(f"Failed to delete file: {path} - {e}")
                    # Continue processing other files even if one fails

        if dry_run:
            logger.info(
                f"[DRY-RUN] Would delete {deleted_count} breaks "
                f"(older than {age_hours} hours)"
            )
        else:
            logger.info(
                f"Deleted {deleted_count} breaks (older than {age_hours} hours)"
            )

        return deleted_count

    finally:
        conn.close()


def main() -> int:
    """Main entry point.

    Returns:
        0 if successful, 1 if error occurred
    """
    parser = argparse.ArgumentParser(
        description="Cleanup old break assets from database and filesystem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete breaks older than 48 hours (default)
  %(prog)s

  # Delete breaks older than 24 hours
  %(prog)s --age-hours 24

  # Preview what would be deleted
  %(prog)s --dry-run

  # Cron entry for daily cleanup at 3 AM
  0 3 * * * /srv/ai_radio/scripts/cleanup_old_breaks.py
        """,
    )

    parser.add_argument(
        "--age-hours",
        type=int,
        default=48,
        help="Delete breaks older than this many hours (default: 48)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.age_hours < 1:
        logger.error("--age-hours must be at least 1")
        return 1

    logger.info("Starting break cleanup service")
    if args.dry_run:
        logger.info("[DRY-RUN MODE] No files will be deleted")

    try:
        deleted_count = cleanup_old_breaks(config.db_path, args.age_hours, args.dry_run)

        if args.dry_run:
            logger.info(
                f"[DRY-RUN] Cleanup complete: would delete {deleted_count} breaks"
            )
        else:
            logger.info(f"Cleanup complete: deleted {deleted_count} breaks")

        return 0

    except sqlite3.Error as e:
        logger.exception(f"Database error during cleanup: {e}")
        return 1
    except OSError as e:
        logger.exception(f"Filesystem error during cleanup: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error during cleanup: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
