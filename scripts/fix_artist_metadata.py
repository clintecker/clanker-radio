#!/usr/bin/env python3
"""Fix artist metadata for all music assets.

Updates all music assets in the database to have artist="Clint Ecker".
Also updates ID3 tags on the actual audio files.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.audio import set_artist_metadata
from ai_radio.config import config


def fix_database_artist(conn):
    """Update all music assets to have artist from config.

    Args:
        conn: SQLite database connection

    Returns:
        int: Number of records updated
    """
    cursor = conn.cursor()
    target_artist = config.music_artist

    # Count current records with wrong artist
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM assets
        WHERE kind = 'music'
        AND (artist IS NULL OR artist != ?)
    """,
        (target_artist,),
    )
    count_before = cursor.fetchone()[0]

    if count_before == 0:
        print(f"✅ All music assets already have correct artist: {target_artist}")
        return 0

    print(f"🔧 Updating {count_before} music assets to artist='{target_artist}'...")

    # Update all music assets
    cursor.execute(
        """
        UPDATE assets
        SET artist = ?
        WHERE kind = 'music'
        AND (artist IS NULL OR artist != ?)
    """,
        (target_artist, target_artist),
    )

    conn.commit()
    updated_count = cursor.rowcount

    print(f"✅ Updated {updated_count} database records")
    return updated_count


def fix_file_id3_tags(conn):
    """Update ID3 tags on all music files.

    Args:
        conn: SQLite database connection

    Returns:
        int: Number of files updated
    """
    cursor = conn.cursor()
    target_artist = config.music_artist

    # Get all music asset paths
    cursor.execute(
        """
        SELECT id, path
        FROM assets
        WHERE kind = 'music'
    """
    )

    assets = cursor.fetchall()
    total = len(assets)

    if total == 0:
        print("⚠️  No music assets found")
        return 0

    print(f"🎵 Updating ID3 tags to '{target_artist}' on {total} music files...")

    updated = 0
    errors = 0

    for asset_id, path_str in assets:
        file_path = Path(path_str)

        if not file_path.exists():
            print(f"⚠️  File not found: {file_path} (asset {asset_id[:8]}...)")
            errors += 1
            continue

        try:
            set_artist_metadata(file_path, target_artist)
            updated += 1

            # Progress indicator every 10 files
            if updated % 10 == 0:
                print(f"   Progress: {updated}/{total} files updated...")

        except Exception as e:
            print(f"❌ Failed to update {file_path}: {e}")
            errors += 1

    print(f"✅ Updated {updated} ID3 tags")
    if errors > 0:
        print(f"⚠️  {errors} errors occurred")

    return updated


def main():
    """Fix artist metadata in database and ID3 tags."""
    db_path = config.db_path

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}", file=sys.stderr)
        return 1

    print(f"📊 Opening database: {db_path}")
    conn = sqlite3.connect(db_path)

    try:
        # Fix database records
        print("\n=== Fixing Database Records ===")
        db_updated = fix_database_artist(conn)

        # Fix ID3 tags
        print("\n=== Fixing ID3 Tags ===")
        files_updated = fix_file_id3_tags(conn)

        print("\n=== Summary ===")
        print(f"Database records updated: {db_updated}")
        print(f"ID3 tags updated: {files_updated}")
        print("✅ Artist metadata fix complete!")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
