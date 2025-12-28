#!/usr/bin/env python3
"""Migrate play_history from filename-based IDs to SHA256-based IDs.

This migration script:
1. Scans bumpers/ and breaks/ directories for audio files
2. Computes SHA256 for each file using extract_metadata()
3. Ingests files into assets table using ingest_audio_file(..., ingest_existing=True)
4. Builds mapping: filename_stem → SHA256
5. Updates play_history with SHA256 IDs using SQL CASE expression
6. Handles orphans (deleted files) with synthetic "orphan_*" records
7. Includes dry-run mode (--dry-run flag)
8. Creates backup before migration (radio.db.bak-pre-migration)
9. Validates results (no orphans, all IDs are SHA256 or orphan_*)
10. Logs mapping to migration_mapping.json
"""

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.audio import extract_metadata
from ai_radio.config import config
from ai_radio.db_assets import get_asset_by_id, insert_asset
from ai_radio.ingest import ingest_audio_file


def is_sha256_hash(s: str) -> bool:
    """Check if string is a valid SHA256 hash (64 hex chars).

    Args:
        s: String to check

    Returns:
        True if string matches SHA256 format
    """
    return bool(re.match(r"^[0-9a-f]{64}$", s))


def is_orphan_id(s: str) -> bool:
    """Check if string is an orphan ID (starts with 'orphan_').

    Args:
        s: String to check

    Returns:
        True if string starts with 'orphan_'
    """
    return s.startswith("orphan_")


def scan_and_hash_files(directory: Path, kind: str) -> dict[str, tuple[str, Path]]:
    """Scan directory for audio files and compute SHA256 for each.

    Args:
        directory: Directory to scan (bumpers/ or breaks/)
        kind: Asset kind ('bumper' or 'break')

    Returns:
        Dict mapping filename_stem → (sha256_hash, file_path)
    """
    if not directory.exists():
        print(f"⚠️  Directory not found: {directory}")
        return {}

    mapping = {}
    audio_extensions = {".mp3", ".flac", ".wav", ".m4a", ".ogg"}

    print(f"\n📂 Scanning {directory} for {kind} files...")

    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
            try:
                metadata = extract_metadata(file_path)
                sha256 = metadata.sha256_id
                stem = file_path.stem

                mapping[stem] = (sha256, file_path)
                print(f"   ✓ {file_path.name} → {sha256[:16]}...")

            except Exception as e:
                print(f"   ⚠️  Failed to process {file_path.name}: {e}")

    print(f"   Found {len(mapping)} {kind} files")
    return mapping


def find_non_sha256_ids(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Find all non-SHA256 asset_ids in play_history.

    Args:
        conn: Database connection

    Returns:
        List of (asset_id, kind) tuples for non-SHA256 IDs
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT asset_id, kind
        FROM play_history
        ORDER BY asset_id
        """
    )

    non_sha256 = []
    for asset_id, kind in cursor.fetchall():
        if not is_sha256_hash(asset_id) and not is_orphan_id(asset_id):
            non_sha256.append((asset_id, kind))

    return non_sha256


def create_orphan_asset(
    conn: sqlite3.Connection, filename_stem: str, kind: str
) -> str:
    """Create synthetic asset record for deleted file.

    Args:
        conn: Database connection
        filename_stem: Original filename stem
        kind: Asset kind

    Returns:
        Orphan asset ID (orphan_{stem})
    """
    orphan_id = f"orphan_{filename_stem}"

    # Check if already exists
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM assets WHERE id = ?", (orphan_id,))
    if cursor.fetchone():
        return orphan_id

    # Insert synthetic orphan record
    insert_asset(
        conn,
        asset_id=orphan_id,
        path=Path(f"[deleted]/{filename_stem}"),
        kind=kind,
        duration_sec=0.0,
        loudness_lufs=None,
        true_peak_dbtp=None,
        title=f"[Deleted] {filename_stem}",
        artist="Unknown",
        album="Deleted Assets",
        energy_level=None,
    )

    return orphan_id


def migrate_play_history(
    conn: sqlite3.Connection,
    mapping: dict[str, str],
    orphan_mapping: dict[str, str],
    dry_run: bool = False,
) -> dict:
    """Update play_history with SHA256 IDs using SQL CASE expression.

    Args:
        conn: Database connection
        mapping: Dict of filename_stem → sha256_hash
        orphan_mapping: Dict of filename_stem → orphan_id
        dry_run: If True, don't commit changes

    Returns:
        Dict with migration statistics
    """
    # Build CASE expression for SQL UPDATE
    case_parts = []

    # Add regular mappings (stem → SHA256)
    for stem, sha256 in mapping.items():
        case_parts.append(f"WHEN asset_id = '{stem}' THEN '{sha256}'")

    # Add orphan mappings (stem → orphan_stem)
    for stem, orphan_id in orphan_mapping.items():
        case_parts.append(f"WHEN asset_id = '{stem}' THEN '{orphan_id}'")

    if not case_parts:
        print("   No mappings to apply")
        return {"updated": 0, "unmapped": 0}

    case_expression = "\n            ".join(case_parts)

    # Get count before update
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM play_history")
    total_count = cursor.fetchone()[0]

    # Count records that will be updated
    all_stems = list(mapping.keys()) + list(orphan_mapping.keys())
    placeholders = ",".join("?" * len(all_stems))
    cursor.execute(
        f"SELECT COUNT(*) FROM play_history WHERE asset_id IN ({placeholders})",
        all_stems,
    )
    update_count = cursor.fetchone()[0]

    # Count unmapped (non-SHA256, non-orphan IDs that we don't have mappings for)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT asset_id)
        FROM play_history
        WHERE asset_id NOT LIKE '________-____-____-____-____________'
    """
    )
    non_sha256_count = cursor.fetchone()[0]
    unmapped_count = non_sha256_count - len(all_stems)

    print(f"\n📊 Migration Statistics:")
    print(f"   Total play_history records: {total_count}")
    print(f"   Records to update: {update_count}")
    print(f"   Unmapped IDs: {unmapped_count}")

    if dry_run:
        print("\n🔍 DRY RUN: Would execute UPDATE but not committing")
        return {"updated": update_count, "unmapped": unmapped_count}

    # Execute update
    update_sql = f"""
        UPDATE play_history
        SET asset_id = CASE
            {case_expression}
            ELSE asset_id
        END
        WHERE asset_id IN ({placeholders})
    """

    cursor.execute(update_sql, all_stems)
    conn.commit()

    print(f"   ✅ Updated {cursor.rowcount} records")

    return {"updated": cursor.rowcount, "unmapped": unmapped_count}


def validate_migration(conn: sqlite3.Connection) -> bool:
    """Validate that migration succeeded.

    Args:
        conn: Database connection

    Returns:
        True if validation passed, False otherwise
    """
    print("\n🔍 Validating migration...")

    cursor = conn.cursor()

    # Check for remaining non-SHA256, non-orphan IDs
    cursor.execute(
        """
        SELECT DISTINCT asset_id
        FROM play_history
        """
    )

    invalid_ids = []
    for (asset_id,) in cursor.fetchall():
        if not is_sha256_hash(asset_id) and not is_orphan_id(asset_id):
            invalid_ids.append(asset_id)

    if invalid_ids:
        print(f"   ❌ Found {len(invalid_ids)} invalid IDs remaining:")
        for asset_id in invalid_ids[:10]:  # Show first 10
            print(f"      - {asset_id}")
        if len(invalid_ids) > 10:
            print(f"      ... and {len(invalid_ids) - 10} more")
        return False

    # Count SHA256 vs orphan IDs
    cursor.execute("SELECT COUNT(DISTINCT asset_id) FROM play_history")
    total_distinct = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(DISTINCT asset_id)
        FROM play_history
        WHERE asset_id LIKE 'orphan_%'
        """
    )
    orphan_count = cursor.fetchone()[0]

    sha256_count = total_distinct - orphan_count

    print(f"   ✅ All IDs are valid")
    print(f"   SHA256 IDs: {sha256_count}")
    print(f"   Orphan IDs: {orphan_count}")
    print(f"   Total distinct IDs: {total_distinct}")

    return True


def main():
    """Main migration orchestration."""
    parser = argparse.ArgumentParser(
        description="Migrate play_history from filename stems to SHA256 hashes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=config.db_path,
        help=f"Path to database (default: {config.db_path})",
    )
    parser.add_argument(
        "--bumpers-dir",
        type=Path,
        default=config.bumpers_path,
        help=f"Path to bumpers directory (default: {config.bumpers_path})",
    )
    parser.add_argument(
        "--breaks-dir",
        type=Path,
        default=config.breaks_path,
        help=f"Path to breaks directory (default: {config.breaks_path})",
    )
    parser.add_argument(
        "--mapping-file",
        type=Path,
        default=Path("migration_mapping.json"),
        help="Path to output mapping file (default: migration_mapping.json)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🔄 SHA256 Asset ID Migration")
    print("=" * 70)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE: No changes will be committed\n")

    # Validate database exists
    if not args.db.exists():
        print(f"❌ Database not found: {args.db}")
        return 1

    # Step 1: Scan and hash files
    print("\n" + "=" * 70)
    print("Step 1: Scanning and hashing audio files")
    print("=" * 70)

    bumper_mapping = scan_and_hash_files(args.bumpers_dir, "bumper")
    break_mapping = scan_and_hash_files(args.breaks_dir, "break")

    # Build combined stem → SHA256 mapping
    stem_to_sha256 = {}
    stem_to_sha256.update(bumper_mapping)
    stem_to_sha256.update(
        {stem: sha256 for stem, (sha256, _) in break_mapping.items()}
    )

    # Step 2: Ingest files into assets table
    print("\n" + "=" * 70)
    print("Step 2: Ingesting files into assets table")
    print("=" * 70)

    conn = sqlite3.connect(args.db)

    try:
        for stem, (sha256, file_path) in bumper_mapping.items():
            # Check if already ingested
            if get_asset_by_id(conn, sha256):
                print(f"   ✓ Already ingested: {file_path.name}")
                continue

            if not args.dry_run:
                try:
                    ingest_audio_file(
                        source_path=file_path,
                        kind="bumper",
                        db_path=args.db,
                        ingest_existing=True,
                    )
                except Exception as e:
                    print(f"   ⚠️  Failed to ingest {file_path.name}: {e}")
            else:
                print(f"   🔍 Would ingest: {file_path.name}")

        for stem, (sha256, file_path) in break_mapping.items():
            # Check if already ingested
            if get_asset_by_id(conn, sha256):
                print(f"   ✓ Already ingested: {file_path.name}")
                continue

            if not args.dry_run:
                try:
                    ingest_audio_file(
                        source_path=file_path,
                        kind="break",
                        db_path=args.db,
                        ingest_existing=True,
                    )
                except Exception as e:
                    print(f"   ⚠️  Failed to ingest {file_path.name}: {e}")
            else:
                print(f"   🔍 Would ingest: {file_path.name}")

        # Step 3: Find non-SHA256 IDs in play_history
        print("\n" + "=" * 70)
        print("Step 3: Finding non-SHA256 IDs in play_history")
        print("=" * 70)

        non_sha256_ids = find_non_sha256_ids(conn)
        print(f"\nFound {len(non_sha256_ids)} non-SHA256 IDs:")

        # Build mapping for play_history update
        migration_mapping = {}
        orphan_mapping = {}

        for asset_id, kind in non_sha256_ids:
            print(f"   {asset_id} ({kind})", end=" → ")

            if asset_id in stem_to_sha256:
                sha256, _ = (
                    bumper_mapping.get(asset_id)
                    or break_mapping.get(asset_id)
                    or (None, None)
                )
                if sha256:
                    migration_mapping[asset_id] = sha256
                    print(f"{sha256[:16]}...")
            else:
                # File deleted, create orphan
                orphan_id = f"orphan_{asset_id}"
                orphan_mapping[asset_id] = orphan_id
                print(f"{orphan_id} [ORPHAN]")

                # Create orphan asset record
                if not args.dry_run:
                    create_orphan_asset(conn, asset_id, kind)
                else:
                    print(f"      🔍 Would create orphan asset: {orphan_id}")

        # Step 4: Create backup (unless dry-run)
        if not args.dry_run:
            print("\n" + "=" * 70)
            print("Step 4: Creating database backup")
            print("=" * 70)

            backup_path = args.db.parent / f"{args.db.stem}.bak-pre-migration"
            print(f"\n💾 Creating backup: {backup_path}")
            shutil.copy2(args.db, backup_path)
            print(f"   ✅ Backup created")

        # Step 5: Update play_history
        print("\n" + "=" * 70)
        print("Step 5: Updating play_history")
        print("=" * 70)

        stats = migrate_play_history(
            conn, migration_mapping, orphan_mapping, dry_run=args.dry_run
        )

        # Step 6: Validate migration (unless dry-run)
        if not args.dry_run:
            print("\n" + "=" * 70)
            print("Step 6: Validating migration")
            print("=" * 70)

            if not validate_migration(conn):
                print("\n❌ Validation failed!")
                return 1

        # Step 7: Save mapping to file
        print("\n" + "=" * 70)
        print("Step 7: Saving migration mapping")
        print("=" * 70)

        mapping_data = {
            "migration_date": datetime.now(timezone.utc).isoformat(),
            "dry_run": args.dry_run,
            "statistics": stats,
            "stem_to_sha256": {
                stem: sha256 for stem, (sha256, _) in {**bumper_mapping, **break_mapping}.items()
            },
            "migration_mapping": migration_mapping,
            "orphan_mapping": orphan_mapping,
        }

        if not args.dry_run:
            with open(args.mapping_file, "w") as f:
                json.dump(mapping_data, f, indent=2)
            print(f"\n💾 Saved mapping to: {args.mapping_file}")
        else:
            print(f"\n🔍 Would save mapping to: {args.mapping_file}")

        # Final summary
        print("\n" + "=" * 70)
        print("✅ Migration Complete!")
        print("=" * 70)

        if args.dry_run:
            print("\n⚠️  This was a DRY RUN - no changes were committed")
            print("   Run without --dry-run to apply changes")
        else:
            print(f"\nUpdated {stats['updated']} records")
            print(f"Created {len(orphan_mapping)} orphan assets")
            if stats["unmapped"] > 0:
                print(f"⚠️  Warning: {stats['unmapped']} IDs remain unmapped")

        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
