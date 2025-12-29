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
from typing import Optional

from ai_radio.audio import extract_metadata, normalize_audio
from ai_radio.config import config
from ai_radio.db_assets import insert_asset, get_asset_by_id


def ingest_audio_file(
    source_path: Path,
    kind: str,
    db_path: Path,
    output_dir: Optional[Path] = None,  # Renamed from music_dir, now optional
    target_lufs: float = -18.0,
    true_peak: float = -1.0,
    ingest_existing: bool = False,  # NEW parameter
) -> dict:
    """Ingest audio file into asset library.

    Args:
        source_path: Path to source audio file
        kind: Asset kind (music, break, bed, safety, bumper)
        db_path: Path to SQLite database
        output_dir: Output directory for normalized files (required when ingest_existing=False)
        target_lufs: Target loudness in LUFS
        true_peak: True peak limit in dBTP
        ingest_existing: If True, register existing file in-place without normalization

    Returns:
        dict with asset information

    Raises:
        ValueError: If ingestion fails or required parameters missing
    """
    # Validate parameters first (before file checks)
    if kind not in ("music", "break", "bed", "safety", "bumper"):
        raise ValueError(f"Invalid kind: {kind}. Must be music, break, bed, safety, or bumper")

    if not ingest_existing and output_dir is None:
        raise ValueError("output_dir is required when ingest_existing=False")

    if not source_path.exists():
        raise ValueError(f"Source file not found: {source_path}")

    # Validate output directory only for new ingestion
    if not ingest_existing:
        if not output_dir.exists():
            raise ValueError(f"Output directory does not exist: {output_dir}")
        if not output_dir.is_dir():
            raise ValueError(f"Output directory path is not a directory: {output_dir}")
        # Test write permission
        test_file = output_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            raise ValueError(f"Output directory is not writable: {output_dir}") from e

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Step 1: Extract metadata to get SHA256 content hash
        print(f"📋 Extracting metadata from {source_path.name}...")
        metadata = extract_metadata(source_path)
        asset_id = metadata.sha256_id

        # Step 2: Check if content already ingested (by SHA256, not path)
        existing = get_asset_by_id(conn, asset_id)
        if existing:
            print(f"⚠️  Content already ingested: {source_path}")
            print(f"   Asset ID: {existing['id']}")
            print(f"   Original path: {existing['path']}")
            return existing

        print(f"   Title: {metadata.title}")
        print(f"   Artist: {metadata.artist}")
        print(f"   Duration: {metadata.duration_sec:.1f}s")

        if ingest_existing:
            # Register existing file without normalization
            print(f"📍 Registering existing file (no normalization)...")
            from ai_radio.audio import measure_loudness

            loudness_stats = measure_loudness(source_path)
            print(f"   Loudness: {loudness_stats['loudness_lufs']:.1f} LUFS")
            print(f"   True Peak: {loudness_stats['true_peak_dbtp']:.1f} dBTP")

            # Use source path as-is
            final_path = source_path
            loudness_lufs = loudness_stats["loudness_lufs"]
            true_peak_dbtp = loudness_stats["true_peak_dbtp"]
        else:
            # Normalize and copy to output directory
            output_path = output_dir / f"{asset_id}.mp3"

            print(f"🔊 Normalizing audio to {target_lufs} LUFS...")
            norm_result = normalize_audio(
                source_path,
                output_path,
                target_lufs=target_lufs,
                true_peak=true_peak,
            )
            print(f"   Loudness: {norm_result['loudness_lufs']:.1f} LUFS")
            print(f"   True Peak: {norm_result['true_peak_dbtp']:.1f} dBTP")

            final_path = output_path
            loudness_lufs = norm_result["loudness_lufs"]
            true_peak_dbtp = norm_result["true_peak_dbtp"]

        # Step 3: Insert into database
        print(f"💾 Inserting asset record into database...")
        try:
            insert_asset(
                conn,
                asset_id=asset_id,
                path=final_path,
                kind=kind,
                duration_sec=metadata.duration_sec,
                loudness_lufs=loudness_lufs,
                true_peak_dbtp=true_peak_dbtp,
                energy_level=50,  # Default medium energy for all tracks
                title=metadata.title,
                artist=config.music_artist,
                album=metadata.album,
            )
        except Exception as db_error:
            # Clean up orphaned normalized file if DB insert fails
            if not ingest_existing and final_path.exists():
                print(f"⚠️  Cleaning up orphaned file: {final_path}", file=sys.stderr)
                final_path.unlink()
            raise

        print(f"✅ Successfully ingested: {metadata.title}")
        print(f"   Asset ID: {asset_id}")
        print(f"   Artist: {config.music_artist}")
        print(f"   Output: {final_path}")

        return {
            "id": asset_id,
            "path": str(final_path),
            "source_path": str(source_path),
            "kind": kind,
            "title": metadata.title,
            "artist": config.music_artist,
            "album": metadata.album,
            "duration_sec": metadata.duration_sec,
            "loudness_lufs": loudness_lufs,
            "true_peak_dbtp": true_peak_dbtp,
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
        choices=["music", "break", "bed", "safety", "bumper"],
        default="music",
        help="Asset kind (default: music)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.paths.db_path,
        help=f"Path to database (default: {config.paths.db_path})",
    )
    parser.add_argument(
        "--music-dir",
        type=Path,
        default=config.paths.music_path,
        help=f"Output directory for normalized files (default: {config.paths.music_path})",
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
            output_dir=args.music_dir,
            target_lufs=args.target_lufs,
            true_peak=args.true_peak,
        )
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
