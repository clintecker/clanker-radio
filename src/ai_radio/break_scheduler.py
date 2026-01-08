"""Break scheduling logic.

Handles selecting and validating breaks for playback.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


class StaleBreakError(Exception):
    """Raised when the most recent break is too old."""

    def __init__(self, break_file: Path, age_minutes: int, threshold_minutes: int):
        self.break_file = break_file
        self.age_minutes = age_minutes
        self.threshold_minutes = threshold_minutes
        super().__init__(
            f"Stale break detected: {break_file.name} is {age_minutes} minutes old "
            f"(threshold: {threshold_minutes} minutes). Break generation may be failing."
        )


def get_fresh_break(breaks_dir: Optional[Path] = None) -> Path:
    """Find the most recent break file and verify it's fresh.

    Args:
        breaks_dir: Directory containing break files. Defaults to config path.

    Returns:
        Path to the most recent fresh break file.

    Raises:
        FileNotFoundError: No break files found.
        StaleBreakError: Most recent break is older than freshness threshold.
    """
    if breaks_dir is None:
        breaks_dir = config.paths.breaks_path

    # Get all break files sorted by modification time (newest first)
    breaks = sorted(
        breaks_dir.glob("break_*.mp3"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not breaks:
        raise FileNotFoundError(f"No breaks available in {breaks_dir}")

    next_break = breaks[0]
    logger.info(f"Found most recent break: {next_break.name}")

    # Check break freshness
    age_seconds = time.time() - next_break.stat().st_mtime
    freshness_seconds = config.operational.break_freshness_minutes * 60

    if age_seconds > freshness_seconds:
        age_minutes = int(age_seconds / 60)
        raise StaleBreakError(
            next_break,
            age_minutes,
            config.operational.break_freshness_minutes
        )

    return next_break
