#!/usr/bin/env python3
"""Diagnostic script to investigate why track selection only finds 1-3 tracks.

Run this on the server to understand the track selection issue.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

def main():
    """Run diagnostics on track selection."""
    db_path = config.db_path

    print(f"Database: {db_path}")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Count total music tracks
    cursor.execute("SELECT COUNT(*) FROM assets WHERE kind = 'music'")
    total_music = cursor.fetchone()[0]
    print(f"\n1. Total music tracks in database: {total_music}")

    # 2. Check how many files actually exist
    cursor.execute("SELECT id, path FROM assets WHERE kind = 'music'")
    tracks = cursor.fetchall()

    existing_count = 0
    missing_tracks = []

    for track_id, path in tracks:
        if Path(path).exists():
            existing_count += 1
        else:
            missing_tracks.append((track_id, path))

    print(f"2. Tracks with valid file paths: {existing_count}/{total_music}")
    print(f"   Missing files: {len(missing_tracks)}")

    if missing_tracks:
        print("\n   Missing track files:")
        for track_id, path in missing_tracks[:10]:  # Show first 10
            print(f"     - {track_id}: {path}")
        if len(missing_tracks) > 10:
            print(f"     ... and {len(missing_tracks) - 10} more")

    # 3. Check recently played exclusion list size
    cursor.execute("""
        SELECT COUNT(*)
        FROM play_history
        WHERE played_at >= datetime('now', '-1 day')
          AND source = 'music'
    """)
    recent_plays = cursor.fetchone()[0]
    print(f"\n3. Tracks played in last 24 hours: {recent_plays}")
    print(f"   Exclusion list size (last 50): min({recent_plays}, 50)")

    # 4. Simulate track selection with different parameters
    print("\n4. Simulating track selection queries:")

    # Get recently played IDs
    cursor.execute("""
        SELECT asset_id
        FROM play_history
        ORDER BY played_at DESC
        LIMIT 50
    """)
    recently_played_ids = [row[0] for row in cursor.fetchall()]

    # Test query without exclusions
    cursor.execute("""
        SELECT COUNT(*)
        FROM assets
        WHERE kind = 'music'
    """)
    without_exclusions = cursor.fetchone()[0]
    print(f"   - Without exclusions: {without_exclusions} tracks available")

    # Test query with exclusions
    if recently_played_ids:
        placeholders = ','.join('?' * len(recently_played_ids))
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM assets
            WHERE kind = 'music'
              AND id NOT IN ({placeholders})
        """, recently_played_ids)
        with_exclusions = cursor.fetchone()[0]
        print(f"   - With exclusions (last 50 plays): {with_exclusions} tracks available")

    # 5. Test actual selection (like enqueue_music.py does)
    print("\n5. Testing actual track selection (requesting 20 tracks):")

    if recently_played_ids:
        placeholders = ','.join('?' * len(recently_played_ids))
        query = f"""
            SELECT id, path, title, artist
            FROM assets
            WHERE kind = 'music'
              AND id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT 20
        """
        cursor.execute(query, recently_played_ids)
    else:
        cursor.execute("""
            SELECT id, path, title, artist
            FROM assets
            WHERE kind = 'music'
            ORDER BY RANDOM()
            LIMIT 20
        """)

    selected = cursor.fetchall()
    print(f"   - Query returned: {len(selected)} tracks")

    # Check which ones actually exist
    valid_count = sum(1 for _, path, _, _ in selected if Path(path).exists())
    print(f"   - Valid file paths: {valid_count}/{len(selected)}")

    if len(selected) < 20:
        print(f"\n   ⚠️  WARNING: Only {len(selected)} tracks returned!")
        print("   Possible causes:")
        if with_exclusions < 20:
            print(f"     - Not enough tracks after exclusions ({with_exclusions} available)")
        if total_music < 50:
            print(f"     - Database has very few music tracks ({total_music} total)")
        if existing_count < total_music:
            print(f"     - Many files are missing ({total_music - existing_count} missing)")

    # 6. Show sample of selected tracks
    if selected:
        print(f"\n6. Sample of selected tracks (first 5):")
        for track_id, path, title, artist in selected[:5]:
            exists = "✓" if Path(path).exists() else "✗"
            print(f"   {exists} {title} by {artist}")
            print(f"      Path: {path}")

    conn.close()

    print("\n" + "=" * 70)
    print("Diagnosis complete!")

    # Summary
    if existing_count < 10:
        print("\n⚠️  CRITICAL: Very few valid music tracks!")
        print("   → Add more music to /srv/ai_radio/assets/music/")
    elif with_exclusions < 20:
        print("\n⚠️  WARNING: Not enough tracks after excluding recent plays")
        print("   → Need more music variety, or reduce RECENT_HISTORY_SIZE")
    elif len(selected) < 20:
        print("\n⚠️  WARNING: Selection query returned fewer than requested")
        print("   → Check for query issues or file validation problems")
    else:
        print("\n✓ Track selection should be working correctly")


if __name__ == "__main__":
    main()
