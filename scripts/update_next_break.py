#!/usr/bin/env python3
"""Update next.mp3 symlink to point to most recent generated break.

This script:
1. Finds the most recent break_*.mp3 file in the breaks directory
2. Backs up the current next.mp3 as last_good.mp3
3. Creates next.mp3 symlink pointing to the latest break

Should be run after each break generation (via ExecStartPost or similar).
"""

import logging
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


def update_next_break() -> bool:
    """Update next.mp3 symlink to most recent break.

    Returns:
        True if successful, False otherwise
    """
    breaks_dir = config.breaks_path

    if not breaks_dir.exists():
        logger.error(f"Breaks directory not found: {breaks_dir}")
        return False

    # Find all generated breaks (skip symlinks)
    break_files = [
        f for f in breaks_dir.glob("break_*.mp3")
        if not f.is_symlink()
    ]

    if not break_files:
        logger.error(f"No break files found in {breaks_dir}")
        return False

    # Sort by modification time, newest first
    latest_break = max(break_files, key=lambda p: p.stat().st_mtime)

    next_symlink = breaks_dir / "next.mp3"
    last_good_symlink = breaks_dir / "last_good.mp3"

    # Back up current next.mp3 as last_good.mp3
    if next_symlink.exists():
        if next_symlink.is_symlink():
            # Remove old last_good if it exists
            if last_good_symlink.exists() or last_good_symlink.is_symlink():
                last_good_symlink.unlink()

            # Copy current next → last_good
            # Use relative target for portability
            current_target = next_symlink.resolve()
            if current_target.exists():
                last_good_symlink.symlink_to(current_target.name)
                logger.info(f"Backed up previous break: {current_target.name} → last_good.mp3")

        # Remove old next.mp3
        next_symlink.unlink()

    # Create new next.mp3 symlink (relative path)
    next_symlink.symlink_to(latest_break.name)
    logger.info(f"Updated next.mp3 → {latest_break.name}")

    return True


def main():
    """Entry point for script."""
    try:
        success = update_next_break()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Failed to update next break: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
