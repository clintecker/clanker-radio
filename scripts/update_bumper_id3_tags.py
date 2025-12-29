#!/usr/bin/env python3
"""Update ID3 tags on all bumper files to match database titles.

Updates all station ID (bumper) files with standardized ID3 tags:
- Title: "Station ID 0xNNNN" (where NNNN is first 4 hex chars of asset ID)
- Artist: Station artist name from config

Usage:
    ./scripts/update_bumper_id3_tags.py
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def update_bumper_id3_tags() -> int:
    """Update ID3 tags on all bumper files.

    Returns:
        Number of files updated
    """
    # Query database for all bumpers
    conn = sqlite3.connect(config.paths.db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, path, title FROM assets
        WHERE kind = 'bumper'
    """)

    bumpers = cursor.fetchall()
    conn.close()

    if not bumpers:
        logger.warning("No bumpers found in database")
        return 0

    logger.info(f"Found {len(bumpers)} bumpers to update")

    updated_count = 0
    error_count = 0

    for asset_id, path, title in bumpers:
        file_path = Path(path)

        if not file_path.exists():
            logger.warning(f"File not found: {path}")
            error_count += 1
            continue

        try:
            # Load MP3 file
            audio = MP3(file_path, ID3=ID3)

            # Ensure ID3 tag exists
            if audio.tags is None:
                audio.add_tags()

            # Set title and artist
            audio.tags["TIT2"] = TIT2(encoding=3, text=title)
            audio.tags["TPE1"] = TPE1(encoding=3, text=config.music_artist)

            # Save changes
            audio.save()

            logger.info(f"Updated: {title} ({file_path.name})")
            updated_count += 1

        except Exception as e:
            logger.error(f"Failed to update {path}: {e}")
            error_count += 1

    logger.info(f"✅ Updated {updated_count} files")
    if error_count > 0:
        logger.warning(f"⚠️  Failed to update {error_count} files")

    return updated_count


def main() -> int:
    """Entry point.

    Returns:
        0 if successful, 1 if failed
    """
    logger.info("Starting bumper ID3 tag update")

    try:
        updated = update_bumper_id3_tags()

        if updated > 0:
            logger.info("Bumper ID3 tags updated successfully")
            return 0
        else:
            logger.error("No bumpers updated")
            return 1

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
