#!/usr/bin/env python3
"""Analyze play statistics from radio database.

Statistical analysis of music tracks, station IDs, and their relationships.
"""

import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config


def get_db_connection():
    """Get database connection."""
    db_path = config.paths.db_path
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    return sqlite3.connect(str(db_path))


def analyze_music_plays(conn) -> Dict:
    """Analyze music track play frequency."""
    cursor = conn.cursor()

    # Get all music plays
    cursor.execute("""
        SELECT asset_id, COUNT(*) as play_count, MAX(played_at) as last_played
        FROM play_history
        WHERE source = 'music'
        GROUP BY asset_id
        ORDER BY play_count DESC
    """)

    plays = cursor.fetchall()

    # Get asset details
    asset_details = {}
    for asset_id, play_count, last_played in plays:
        cursor.execute("""
            SELECT title, artist, energy_level
            FROM assets
            WHERE id = ?
        """, (asset_id,))

        result = cursor.fetchone()
        if result:
            title, artist, energy = result
            asset_details[asset_id] = {
                "title": title,
                "artist": artist,
                "energy": energy,
                "play_count": play_count,
                "last_played": last_played
            }

    return asset_details


def analyze_station_id_plays(conn) -> Dict:
    """Analyze station ID play frequency."""
    cursor = conn.cursor()

    # Get all station ID plays (source = 'bumper')
    cursor.execute("""
        SELECT asset_id, COUNT(*) as play_count, MAX(played_at) as last_played
        FROM play_history
        WHERE source = 'bumper'
        GROUP BY asset_id
        ORDER BY play_count DESC
    """)

    plays = cursor.fetchall()

    station_ids = {}
    for asset_id, play_count, last_played in plays:
        # Get asset details
        cursor.execute("SELECT path FROM assets WHERE id = ?", (asset_id,))
        result = cursor.fetchone()
        file_path = result[0] if result else "unknown"
        filename = Path(file_path).name if file_path else f"asset_{asset_id}"

        station_ids[filename] = {
            "play_count": play_count,
            "last_played": last_played,
            "path": file_path
        }

    return station_ids


def analyze_sequential_patterns(conn) -> Dict:
    """Analyze what plays after station IDs vs what plays after music."""
    cursor = conn.cursor()

    # Get all plays in chronological order
    cursor.execute("""
        SELECT source, asset_id, played_at
        FROM play_history
        ORDER BY played_at ASC
    """)

    all_plays = cursor.fetchall()

    # Track transitions
    after_station_id = []
    after_music = []

    for i in range(1, len(all_plays)):
        prev_type = all_plays[i-1][0]
        curr_type = all_plays[i][0]
        curr_asset_id = all_plays[i][1]

        if prev_type == 'bumper' and curr_type == 'music':
            after_station_id.append(curr_asset_id)
        elif prev_type == 'music' and curr_type == 'music':
            after_music.append(curr_asset_id)

    # Count frequencies
    after_id_counts = Counter(after_station_id)
    after_music_counts = Counter(after_music)

    # Get top 10 most common tracks after station IDs
    cursor = conn.cursor()
    top_after_ids = []
    for asset_id, count in after_id_counts.most_common(10):
        cursor.execute("SELECT title, artist FROM assets WHERE id = ?", (asset_id,))
        result = cursor.fetchone()
        if result:
            title, artist = result
            top_after_ids.append({
                "title": title,
                "artist": artist,
                "count": count
            })

    return {
        "total_after_station_id": len(after_station_id),
        "total_after_music": len(after_music),
        "unique_after_station_id": len(after_id_counts),
        "unique_after_music": len(after_music_counts),
        "top_after_station_ids": top_after_ids
    }


def analyze_time_gaps(conn) -> Dict:
    """Analyze time gaps between station IDs."""
    cursor = conn.cursor()

    # Get all station ID plays in order
    cursor.execute("""
        SELECT played_at
        FROM play_history
        WHERE source = 'bumper'
        ORDER BY played_at ASC
    """)

    plays = [row[0] for row in cursor.fetchall()]

    if len(plays) < 2:
        return {"error": "Not enough station ID plays to analyze"}

    # Calculate gaps
    gaps = []
    for i in range(1, len(plays)):
        prev_time = datetime.fromisoformat(plays[i-1])
        curr_time = datetime.fromisoformat(plays[i])
        gap_minutes = (curr_time - prev_time).total_seconds() / 60
        gaps.append(gap_minutes)

    avg_gap = sum(gaps) / len(gaps)
    min_gap = min(gaps)
    max_gap = max(gaps)

    return {
        "total_station_ids": len(plays),
        "average_gap_minutes": round(avg_gap, 2),
        "min_gap_minutes": round(min_gap, 2),
        "max_gap_minutes": round(max_gap, 2),
        "expected_gap_minutes": 15,  # Should be ~15 min (plays at :15, :30, :45)
    }


def print_report(music_plays, station_id_plays, patterns, time_gaps):
    """Print comprehensive statistical report."""
    print("=" * 80)
    print("RADIO PLAY STATISTICS")
    print("=" * 80)
    print()

    # Music Statistics
    print("MUSIC PLAY FREQUENCY")
    print("-" * 80)
    total_music_plays = sum(track["play_count"] for track in music_plays.values())
    print(f"Total music plays: {total_music_plays}")
    print(f"Unique tracks played: {len(music_plays)}")
    print()

    print("Top 10 Most Played Tracks:")
    sorted_music = sorted(music_plays.items(), key=lambda x: x[1]["play_count"], reverse=True)
    for i, (asset_id, data) in enumerate(sorted_music[:10], 1):
        print(f"{i:2d}. {data['title']:40s} - {data['artist']:20s} ({data['play_count']} plays)")
    print()

    print("Bottom 10 Least Played Tracks:")
    for i, (asset_id, data) in enumerate(sorted_music[-10:], 1):
        print(f"{i:2d}. {data['title']:40s} - {data['artist']:20s} ({data['play_count']} plays)")
    print()

    # Station ID Statistics
    print("STATION ID PLAY FREQUENCY")
    print("-" * 80)
    total_id_plays = sum(data["play_count"] for data in station_id_plays.values())
    print(f"Total station ID plays: {total_id_plays}")
    print(f"Unique station IDs: {len(station_id_plays)}")
    print()

    sorted_ids = sorted(station_id_plays.items(), key=lambda x: x[1]["play_count"], reverse=True)
    for filename, data in sorted_ids:
        print(f"  {filename:50s} ({data['play_count']} plays)")
    print()

    # Time Gap Analysis
    print("STATION ID TIMING ANALYSIS")
    print("-" * 80)
    if "error" not in time_gaps:
        print(f"Total station IDs played: {time_gaps['total_station_ids']}")
        print(f"Average gap between IDs: {time_gaps['average_gap_minutes']:.2f} minutes")
        print(f"Expected gap: {time_gaps['expected_gap_minutes']} minutes")
        print(f"Min gap: {time_gaps['min_gap_minutes']:.2f} minutes")
        print(f"Max gap: {time_gaps['max_gap_minutes']:.2f} minutes")

        deviation = abs(time_gaps['average_gap_minutes'] - time_gaps['expected_gap_minutes'])
        if deviation > 2:
            print(f"\n⚠ WARNING: Average gap deviates by {deviation:.2f} minutes from expected!")
    else:
        print(time_gaps['error'])
    print()

    # Sequential Patterns
    print("SEQUENTIAL PLAY PATTERNS")
    print("-" * 80)
    print(f"Total music plays after station IDs: {patterns['total_after_station_id']}")
    print(f"Unique tracks after station IDs: {patterns['unique_after_station_id']}")
    print()

    print("Top 10 tracks that play most often after station IDs:")
    for i, track in enumerate(patterns['top_after_station_ids'], 1):
        print(f"{i:2d}. {track['title']:40s} - {track['artist']:20s} ({track['count']} times)")
    print()

    # Check for bias
    if patterns['total_after_station_id'] > 0:
        avg_expected = patterns['total_after_station_id'] / len(music_plays)
        top_track_count = patterns['top_after_station_ids'][0]['count'] if patterns['top_after_station_ids'] else 0

        if top_track_count > avg_expected * 2:
            print(f"⚠ POTENTIAL BIAS: Top track plays {top_track_count} times after station IDs")
            print(f"  (Expected average: {avg_expected:.2f} times per track)")

    print()
    print("=" * 80)


def main():
    """Run statistical analysis."""
    try:
        conn = get_db_connection()

        print("Analyzing database...")
        print()

        # Run all analyses
        music_plays = analyze_music_plays(conn)
        station_id_plays = analyze_station_id_plays(conn)
        patterns = analyze_sequential_patterns(conn)
        time_gaps = analyze_time_gaps(conn)

        # Print report
        print_report(music_plays, station_id_plays, patterns, time_gaps)

        conn.close()
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
