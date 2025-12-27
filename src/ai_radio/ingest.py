#!/usr/bin/env python3
"""Ingest audio files into the asset library.

This script orchestrates the complete ingestion pipeline:
1. Extract metadata from source file
2. Normalize audio to broadcast standards
3. Store normalized file in music directory
4. Insert asset record into database
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from ai_radio.audio import extract_metadata, normalize_audio
from ai_radio.config import config
from ai_radio.db_assets import insert_asset, get_asset_by_path


def ingest_audio_file(
    source_path: Path,
    kind: str,
    db_path: Path,
    music_dir: Path,
    target_lufs: float = -18.0,
    true_peak: float = -1.0,
) -> dict:
    """Ingest audio file into asset library.

    Args:
        source_path: Path to source audio file
        kind: Asset kind (music, break, bed, safety)
        db_path: Path to SQLite database
        music_dir: Directory for normalized music files
        target_lufs: Target loudness in LUFS
        true_peak: True peak limit in dBTP

    Returns:
        dict with asset information

    Raises:
        ValueError: If ingestion fails
    """
    if not source_path.exists():
        raise ValueError(f"Source file not found: {source_path}")

    if kind not in ("music", "break", "bed", "safety"):
        raise ValueError(f"Invalid kind: {kind}. Must be music, break, bed, or safety")

    # Validate music directory exists and is writable
    if not music_dir.exists():
        raise ValueError(f"Music directory does not exist: {music_dir}")
    if not music_dir.is_dir():
        raise ValueError(f"Music directory path is not a directory: {music_dir}")
    # Test write permission by attempting to create a temp file
    test_file = music_dir / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        raise ValueError(f"Music directory is not writable: {music_dir}") from e

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Check if file already ingested
        existing = get_asset_by_path(conn, source_path)
        if existing:
            print(f"⚠️  File already ingested: {source_path}")
            print(f"   Asset ID: {existing['id']}")
            return existing

        # Step 1: Extract metadata
        print(f"📋 Extracting metadata from {source_path.name}...")
        metadata = extract_metadata(source_path)
        print(f"   Title: {metadata.title}")
        print(f"   Artist: {metadata.artist}")
        print(f"   Duration: {metadata.duration_sec:.1f}s")

        # Step 2: Normalize audio
        asset_id = metadata.sha256_id
        output_path = music_dir / f"{asset_id}.mp3"

        print(f"🔊 Normalizing audio to {target_lufs} LUFS...")
        norm_result = normalize_audio(
            source_path,
            output_path,
            target_lufs=target_lufs,
            true_peak=true_peak,
        )
        print(f"   Loudness: {norm_result['loudness_lufs']:.1f} LUFS")
        print(f"   True Peak: {norm_result['true_peak_dbtp']:.1f} dBTP")

        # Step 3: Insert into database
        print(f"💾 Inserting asset record into database...")
        try:
            insert_asset(
                conn,
                asset_id=asset_id,
                path=output_path,  # Store normalized file path, not staging path
                kind=kind,
                duration_sec=metadata.duration_sec,
                loudness_lufs=norm_result["loudness_lufs"],
                true_peak_dbtp=norm_result["true_peak_dbtp"],
                title=metadata.title,
                artist=metadata.artist,
                album=metadata.album,
            )
        except Exception as db_error:
            # Clean up orphaned normalized file if DB insert fails
            if output_path.exists():
                print(f"⚠️  Cleaning up orphaned file: {output_path}", file=sys.stderr)
                output_path.unlink()
            raise

        print(f"✅ Successfully ingested: {metadata.title}")
        print(f"   Asset ID: {asset_id}")
        print(f"   Output: {output_path}")

        return {
            "id": asset_id,
            "path": str(output_path),  # Database path (normalized file location)
            "source_path": str(source_path),  # Original staging path for reference
            "kind": kind,
            "title": metadata.title,
            "artist": metadata.artist,
            "album": metadata.album,
            "duration_sec": metadata.duration_sec,
            "loudness_lufs": norm_result["loudness_lufs"],
            "true_peak_dbtp": norm_result["true_peak_dbtp"],
        }

    except Exception as e:
        print(f"❌ Ingestion failed: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main():
    """Command-line interface for audio ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest audio files into the asset library"
    )
    parser.add_argument(
        "source_path",
        type=Path,
        help="Path to source audio file",
    )
    parser.add_argument(
        "--kind",
        choices=["music", "break", "bed", "safety"],
        default="music",
        help="Asset kind (default: music)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.db_path,
        help=f"Path to database (default: {config.db_path})",
    )
    parser.add_argument(
        "--music-dir",
        type=Path,
        default=config.music_path,
        help=f"Output directory for normalized files (default: {config.music_path})",
    )
    parser.add_argument(
        "--target-lufs",
        type=float,
        default=-18.0,
        help="Target loudness in LUFS (default: -18.0)",
    )
    parser.add_argument(
        "--true-peak",
        type=float,
        default=-1.0,
        help="True peak limit in dBTP (default: -1.0)",
    )

    args = parser.parse_args()

    try:
        result = ingest_audio_file(
            source_path=args.source_path,
            kind=args.kind,
            db_path=args.db,
            music_dir=args.music_dir,
            target_lufs=args.target_lufs,
            true_peak=args.true_peak,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
