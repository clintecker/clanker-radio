#!/usr/bin/env python3
"""One-time migration: Fix timestamp formats in play_history.

Before: datetime('now') format: "2025-12-23 00:15:09" (space, no timezone)
After: Python isoformat: "2025-12-23T00:15:09.000000+00:00" (T separator, timezone)

This ensures consistent sorting in DESC queries.
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ai_radio.config import config

def fix_timestamps():
    """Fix timestamp formats in play_history table."""
    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()

    # Find all records with space format (YYYY-MM-DD HH:MM:SS)
    cursor.execute(
        """
        SELECT rowid, played_at
        FROM play_history
        WHERE played_at LIKE '% %'
          AND played_at NOT LIKE '%T%'
        """
    )

    rows = cursor.fetchall()
    print(f"Found {len(rows)} records with incorrect timestamp format")

    if not rows:
        print("No records to fix!")
        conn.close()
        return

    # Convert each timestamp
    fixed_count = 0
    for rowid, old_timestamp in rows:
        try:
            # Parse old format: "2025-12-23 00:15:09"
            dt = datetime.strptime(old_timestamp, "%Y-%m-%d %H:%M:%S")

            # Assume UTC timezone (Liquidsoap timestamps are UTC)
            dt = dt.replace(tzinfo=timezone.utc)

            # Convert to ISO format with timezone
            new_timestamp = dt.isoformat()

            # Update record
            cursor.execute(
                "UPDATE play_history SET played_at = ? WHERE rowid = ?",
                (new_timestamp, rowid)
            )

            fixed_count += 1
            print(f"  Fixed rowid={rowid}: {old_timestamp} → {new_timestamp}")

        except Exception as e:
            print(f"  ERROR fixing rowid={rowid}: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"\nFixed {fixed_count}/{len(rows)} records")

if __name__ == "__main__":
    print("Starting timestamp migration...")
    fix_timestamps()
    print("Migration complete!")
