# Phase 6: Observability & Monitoring - Validation Results

**Date:** 2025-12-18
**Validator:** Gemini-3-Pro (via PAL MCP codereview)
**Status:** 🔴 CRITICAL ISSUES FOUND

## Executive Summary

Phase 6 provides functional observability tooling with good separation of concerns, but has **critical integration gaps** between Liquidsoap and the play history database. Without a mechanism to actually record plays when tracks play, the entire observability layer is non-functional. Additionally, the database schema deviates from SOW Section 6 requirements.

**Risk Assessment:**
- **Deployment Blocker:** No integration between Liquidsoap and play history recording
- **Contract Violation:** Schema doesn't match SOW Section 6 specification
- **Operational Risk:** Secret handling pattern breaks in dashboard script

---

## Issues Found

### 🔴 CRITICAL (1 issue)

#### Issue 1: Missing Integration Between Liquidsoap and Play History
**Location:** Entire Phase 6 architecture
**Context:** Task 1, play_history.py module

**Problem:**
The plan implements `record_play()` in Python but provides **NO mechanism to invoke it when a track actually plays**. There is no connection between Liquidsoap playout events and the database logging function.

**Impact:**
- Play history database will remain empty
- Anti-repetition logic in Phase 5 will fail (returns empty list)
- **The entire observability system is non-functional**
- SOW Section 14 requirements not met

**Fix:**
Create a CLI entry point and configure Liquidsoap to call it on track transitions.

**Step 1: Create CLI entry point**

Create `/srv/ai_radio/scripts/record_play.py`:

```python
#!/usr/bin/env python3
"""
AI Radio Station - Record Play CLI
Called by Liquidsoap on track transitions
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.play_history import record_play
from ai_radio.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: record_play.py <asset_id> [queue_name]")
        sys.exit(1)

    asset_id = sys.argv[1]
    queue_name = sys.argv[2] if len(sys.argv) > 2 else "music"

    config = get_config()

    if record_play(config.db_path, asset_id, queue_name):
        logger.info(f"Recorded play: {asset_id}")
        sys.exit(0)
    else:
        logger.error(f"Failed to record play: {asset_id}")
        sys.exit(1)
```

**Step 2: Update radio.liq to call recorder**

Add to `/srv/ai_radio/radio.liq` (Phase 3):

```liquidsoap
# Play history tracking (Phase 6 integration)
def on_track_play(m) =
  asset_id = m["filename"]  # Or extract ID from metadata
  queue = m.get(default="music", "queue")

  # Call Python recorder in background
  ignore(
    process.run(
      "/srv/ai_radio/.venv/bin/python \
       /srv/ai_radio/scripts/record_play.py \
       #{asset_id} #{queue} &"
    )
  )
end

# Attach to music source
music_queue = request.queue(id="music")
music_queue.on_track(on_track_play)
```

**Validation:**
```bash
# After implementing, verify plays are recorded:
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM play_history WHERE played_at >= datetime('now', '-1 hour');"
# Should show increasing count as tracks play
```

---

### 🟠 HIGH (2 issues)

#### Issue 2: Schema Mismatch with SOW Section 6
**Location:** `play_history` table schema
**Line:** Task 1, Step 1, lines 40-50

**Problem:**
The proposed schema deviates from the Non-Negotiable Data Model in SOW Section 6:
- **Missing:** `hour_bucket` column (required for analytics)
- **Mismatch:** SOW specifies `source` column; plan uses `queue_name`

**SOW Requirement (Section 6):**
```
play_history:
- id (autoincrement)
- asset_id (FK to assets)
- played_at (ISO8601 UTC)
- source (text: music|override|break|bumper)
- hour_bucket (text: ISO8601 hour truncated, e.g., 2025-12-18T15:00:00Z)
```

**Fix:**
Update schema to match SOW exactly:

```sql
CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    played_at TEXT NOT NULL,        -- ISO8601 UTC
    source TEXT NOT NULL,            -- music|override|break|bumper
    hour_bucket TEXT NOT NULL,       -- e.g., 2025-12-18T15:00:00Z
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);
CREATE INDEX IF NOT EXISTS idx_play_history_asset_id ON play_history(asset_id);
CREATE INDEX IF NOT EXISTS idx_play_history_hour_bucket ON play_history(hour_bucket);
```

**Update record_play function:**

```python
def record_play(
    db_path: Path,
    asset_id: str,
    source: str = "music"  # Changed from queue_name
) -> bool:
    """
    Record that an asset was played

    Args:
        db_path: Database path
        asset_id: Asset ID
        source: Play source (music|override|break|bumper)

    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc)
        played_at = now.isoformat()

        # Calculate hour_bucket (SOW Section 6 requirement)
        hour_bucket = now.replace(
            minute=0,
            second=0,
            microsecond=0
        ).isoformat()

        cursor.execute(
            """
            INSERT INTO play_history (asset_id, played_at, source, hour_bucket)
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, played_at, source, hour_bucket)
        )

        conn.commit()
        conn.close()

        logger.info(f"Recorded play: {asset_id} from {source}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Failed to record play: {e}")
        return False
```

---

#### Issue 3: Incorrect Secret Handling in Dashboard Script
**Location:** `status-dashboard.sh`
**Line:** Task 3, Step 1, line 473

**Problem:**
The script attempts to `cat /srv/ai_radio/.secrets/icecast_admin_password`, but Phase 4 established `.secrets` as a `KEY=VALUE` dotenv file (not a single-value file).

**Current (Broken):**
```bash
LISTENERS=$(curl -s http://admin:$(cat /srv/ai_radio/.secrets/icecast_admin_password)@...)
```

**This will:**
- Fail to find `/srv/ai_radio/.secrets/icecast_admin_password` (doesn't exist)
- OR expose entire secrets file if user created this file manually

**Fix:**
Parse the KEY=VALUE format correctly:

```bash
# In status-dashboard.sh, line 473:
ICECAST_PASS=$(grep '^ICECAST_ADMIN_PASSWORD=' /srv/ai_radio/.secrets | cut -d= -f2)
LISTENERS=$(curl -s "http://admin:${ICECAST_PASS}@127.0.0.1:8000/admin/stats" | grep -oP '<Listeners>\K[0-9]+' | head -1 || echo "?")
```

---

### 🟡 MEDIUM (2 issues)

#### Issue 4: Deviation from SOW Section 11 (Health Check Format)
**Location:** `health-check.sh`
**Context:** Task 2

**Problem:**
SOW Section 11 specifically requires a `healthcheck.py` script that writes:
- `metrics.json` - Current system state
- `jobs.jsonl` - Job execution log

Phase 6 provides a Bash script (`health-check.sh`) that only prints to stdout. This breaks the observability contract expected by other tools or SOW compliance audits.

**Fix (Option A - Strict SOW Compliance):**
Implement `healthcheck.py` that writes the required JSON files:

```python
#!/usr/bin/env python3
"""AI Radio Station - Health Check (SOW Section 11)"""
import json
from pathlib import Path
from datetime import datetime

METRICS_FILE = Path("/srv/ai_radio/metrics.json")
JOBS_FILE = Path("/srv/ai_radio/jobs.jsonl")

def check_health():
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "icecast": systemctl_check("icecast2"),
            "liquidsoap": systemctl_check("ai-radio-liquidsoap"),
            # ... other checks
        },
        "queues": {
            "music": get_queue_depth("music"),
            "breaks": get_queue_depth("breaks"),
        },
        "stream": check_stream_status(),
    }

    # Write metrics.json (SOW requirement)
    with open(METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2)

    # Append to jobs.jsonl (SOW requirement)
    with open(JOBS_FILE, 'a') as f:
        job_entry = {
            "timestamp": datetime.now().isoformat(),
            "job": "healthcheck",
            "status": "success" if all_checks_pass(metrics) else "failure",
            "metrics": metrics
        }
        f.write(json.dumps(job_entry) + '\n')

if __name__ == "__main__":
    check_health()
```

**Fix (Option B - Document Deviation):**
If `health-check.sh` is preferred, explicitly document this as a change control item:

"**Change Control:** SOW Section 11 requires `healthcheck.py` writing JSON files. This implementation uses `health-check.sh` printing to stdout for operational simplicity. JSON output can be added if required for compliance."

---

#### Issue 5: get_recently_played_ids Query Mismatch
**Location:** `play_history.py`
**Line:** Task 1, Step 2, line 153

**Problem:**
The `get_recently_played_ids` function queries by `queue_name`, but the schema (after SOW fix) uses `source`.

**Fix:**
Update query parameter:

```python
def get_recently_played_ids(
    db_path: Path,
    source: str = "music",  # Changed from queue_name
    hours: int = 24,
    limit: int = 50
) -> list[str]:
    """
    Get recently played asset IDs

    Args:
        db_path: Database path
        source: Play source to query (music|override|break|bumper)
        hours: Look back this many hours
        limit: Maximum IDs to return

    Returns:
        List of asset IDs (most recent first)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        cursor.execute(
            """
            SELECT DISTINCT asset_id
            FROM play_history
            WHERE source = ?  # Changed from queue_name
              AND played_at >= ?
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (source, cutoff, limit)
        )

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Failed to get recent plays: {e}")
        return []
```

---

### 🟢 LOW (1 issue)

#### Issue 6: Foreign Keys Not Explicitly Enabled
**Location:** Database schema
**Line:** Task 1, Step 1

**Problem:**
SQLite defaults to `PRAGMA foreign_keys = OFF`. The schema creates foreign key constraints but doesn't ensure they're enforced.

**Fix:**
Add pragma to migration script:

```bash
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 << 'EOF'
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS play_history (
    ...
);
EOF
```

---

## Positive Aspects

✅ **Practical Tooling:** The `health-check.sh` and `status-dashboard.sh` provide excellent, immediate visibility for operators without complex monitoring infrastructure

✅ **Safety:** Use of `set -euo pipefail` in bash scripts and parameterized SQL queries demonstrates good security practices

✅ **Clean Separation:** Play history logic is well-encapsulated in its own module, easy to test and maintain

✅ **SQL Injection Protection:** All queries use parameterized statements

✅ **Resource Management:** Proper connection cleanup in all functions

---

## Recommended Fixes Priority

### Must Fix Before Deployment (CRITICAL):

1. **Implement Liquidsoap Integration:** Create `record_play.py` CLI and add `on_track` hooks to `radio.liq`

### Must Fix Before Launch (HIGH):

2. **Fix Database Schema:** Update `play_history` table to match SOW Section 6 (`source`, `hour_bucket`)
3. **Fix Secret Parsing:** Update dashboard script to parse `KEY=VALUE` format

### Should Fix (MEDIUM):

4. **SOW Health Check Compliance:** Implement `healthcheck.py` writing JSON files OR document deviation
5. **Update Query Parameters:** Change `queue_name` → `source` in all queries

### Nice to Have (LOW):

6. **Enable Foreign Keys:** Add `PRAGMA foreign_keys = ON` to migration

---

## Top 3 Fixes (Quick Win)

1. **Liquidsoap Integration** (30 minutes)
   - Create `record_play.py` CLI wrapper
   - Add `on_track` hook to `radio.liq`
   - Test that plays are recorded

2. **Schema Fix** (15 minutes)
   - Update CREATE TABLE with `source` and `hour_bucket`
   - Update `record_play()` function with hour_bucket calculation
   - Re-run migration

3. **Secret Parsing Fix** (5 minutes)
   - Change `cat` to `grep | cut` pattern
   - Location: `status-dashboard.sh:473`

**Total time to fix critical issues: ~50 minutes**

---

## SOW Compliance

⚠️  Section 6: Database schema (play_history) - requires fixes
⚠️  Section 11: Health check format - deviation from spec
✅ Section 14: Operational visibility - tools functional after fixes
✅ Section 14: Play history tracking - architecture sound
✅ Section 3: Simple, maintainable tooling

---

## Summary

**Overall Assessment:** Phase 6 provides solid observability tooling with good security practices and practical operator interfaces. However, **the critical missing piece is the integration between Liquidsoap and the play history database** - without this connection, the entire observability layer is non-functional.

**Deployment Readiness:** 🔴 **NOT READY** - Critical integration gap

**After Fixes Applied:** 🟢 **READY FOR DEPLOYMENT**

---

## Validation Checklist

After applying fixes, verify:

- [ ] Tracks playing through Liquidsoap create entries in `play_history` table
- [ ] `play_history` schema matches SOW Section 6 exactly
- [ ] Dashboard script successfully fetches listener count via Icecast admin API
- [ ] `get_recently_played_ids()` returns actual recent plays
- [ ] Health check script runs without errors
- [ ] `sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT * FROM play_history LIMIT 10;"` shows plays

---

**Validator Notes:**
The core observability design is sound and pragmatic for a single-server deployment. The fixes required are straightforward integration work rather than architectural changes. After connecting Liquidsoap to the database and aligning the schema with SOW Section 6, this phase will be production-ready.
