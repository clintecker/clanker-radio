#!/usr/bin/env python3
"""Batch ingest existing bumpers and breaks into assets table.

This script scans the bumpers/ and breaks/ directories and ingests all audio files
that are not already in the assets table. It uses the existing ingestion pipeline
to ensure consistency.

Usage:
    ./scripts/batch_ingest_assets.py [--dry-run] [--kind bumper|break|all]

Exit codes:
    0: Success
    1: Error occurred
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.ingest import ingest_audio_file
from ai_radio.db_assets import get_asset_by_path
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def scan_directory(directory: Path, kind: str, extensions=None) -> list[Path]:
    """Scan directory for audio files.

    Args:
        directory: Directory to scan
        kind: Asset kind (bumper/break)
        extensions: List of file extensions to include (default: .mp3, .wav)

    Returns:
        List of audio file paths
    """
    if extensions is None:
        extensions = [".mp3", ".wav", ".ogg"]

    files = []
    for ext in extensions:
        files.extend(directory.glob(f"*{ext}"))

    logger.info(f"Found {len(files)} {kind} files in {directory}")
    return sorted(files)


def batch_ingest(
    directory: Path,
    kind: str,
    dry_run: bool = False,
    skip_existing: bool = True
) -> tuple[int, int, int]:
    """Batch ingest all files in directory.

    Args:
        directory: Directory containing audio files
        kind: Asset kind (bumper/break)
        dry_run: If True, only show what would be ingested
        skip_existing: If True, skip files already in database

    Returns:
        Tuple of (success_count, skip_count, error_count)
    """
    files = scan_directory(directory, kind)

    if not files:
        logger.warning(f"No files found in {directory}")
        return 0, 0, 0

    success_count = 0
    skip_count = 0
    error_count = 0

    # For MP3/WAV pairs, prefer MP3 (already normalized)
    files_by_stem = {}
    for file_path in files:
        stem = file_path.stem
        ext = file_path.suffix

        if stem not in files_by_stem:
            files_by_stem[stem] = file_path
        elif ext == ".mp3" and files_by_stem[stem].suffix != ".mp3":
            # Prefer MP3 over WAV
            files_by_stem[stem] = file_path

    unique_files = list(files_by_stem.values())
    logger.info(f"Processing {len(unique_files)} unique files (after deduplication)")

    for file_path in unique_files:
        logger.info(f"Processing: {file_path.name}")

        if dry_run:
            logger.info(f"  [DRY RUN] Would ingest as kind={kind}")
            success_count += 1
            continue

        # Check if already ingested
        if skip_existing:
            conn = sqlite3.connect(config.db_path)
            try:
                existing = get_asset_by_path(conn, file_path)
                if existing:
                    logger.info(f"  ⏭️  Already in database (asset_id={existing['id']})")
                    skip_count += 1
                    continue
            finally:
                conn.close()

        try:
            # Ingest the file
            result = ingest_audio_file(
                source_path=file_path,
                kind=kind,
                db_path=config.db_path,
                music_dir=config.assets_path / kind + "s",  # bumpers or breaks directory
                target_lufs=-18.0,
                true_peak=-1.0,
            )
            logger.info(f"  ✅ Ingested successfully (asset_id={result['id']})")
            success_count += 1

        except Exception as e:
            logger.error(f"  ❌ Failed to ingest: {e}")
            error_count += 1

    return success_count, skip_count, error_count


def main():
    """Entry point for batch ingestion."""
    parser = argparse.ArgumentParser(
        description="Batch ingest existing bumpers and breaks into assets table"
    )
    parser.add_argument(
        "--kind",
        choices=["bumper", "break", "all"],
        default="all",
        help="Type of assets to ingest (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without actually doing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest files even if already in database",
    )

    args = parser.parse_args()

    total_success = 0
    total_skip = 0
    total_error = 0

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    # Ingest bumpers
    if args.kind in ("bumper", "all"):
        logger.info("=" * 60)
        logger.info("INGESTING BUMPERS (Station IDs)")
        logger.info("=" * 60)
        success, skip, error = batch_ingest(
            directory=config.bumpers_path,
            kind="bumper",
            dry_run=args.dry_run,
            skip_existing=not args.force,
        )
        total_success += success
        total_skip += skip
        total_error += error

    # Ingest breaks
    if args.kind in ("break", "all"):
        logger.info("=" * 60)
        logger.info("INGESTING BREAKS (News Breaks)")
        logger.info("=" * 60)
        success, skip, error = batch_ingest(
            directory=config.breaks_path,
            kind="break",
            dry_run=args.dry_run,
            skip_existing=not args.force,
        )
        total_success += success
        total_skip += skip
        total_error += error

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Successfully ingested: {total_success}")
    logger.info(f"⏭️  Skipped (already in DB): {total_skip}")
    logger.info(f"❌ Errors: {total_error}")

    if args.dry_run:
        logger.info("🔍 This was a dry run - no changes were made")

    return 0 if total_error == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
