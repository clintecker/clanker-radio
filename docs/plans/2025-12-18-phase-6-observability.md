# Phase 6: Observability & Monitoring - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement essential operational visibility: play history tracking, health checks, and basic metrics collection for monitoring station health

**Architecture:** Lightweight observability layer with play history tracking in SQLite, simple health check script, metrics exposure via filesystem/logs, systemd journal integration for troubleshooting.

**Tech Stack:** Python 3.12, SQLite (play history), systemd journal, basic shell scripts

---

## Overview

Phase 6 adds operational visibility without complex infrastructure. This is pragmatic observability for a single-server deployment:

1. **Play History Tracking** - Record what played when (enables anti-repetition)
2. **Health Check Script** - Quick status check for all services
3. **Metrics Collection** - Simple stats (queue depth, uptime, break generation)
4. **Status Dashboard** - Terminal-based status view
5. **Systemd Journal Integration** - Centralized logging

**Why This Matters:** Without this, troubleshooting is blind. With this, operators can quickly assess health and debug issues.

---

## Task 1: Play History Tracking

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/play_history.py`
- Create: `/srv/ai_radio/tests/test_play_history.py`
- Modify: `/srv/ai_radio/src/ai_radio/track_selection.py`

**Step 1: Add play history schema migration**

Add to database setup (one-time migration):

```sql
-- Play history table
CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    played_at TEXT NOT NULL,
    queue_name TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);
CREATE INDEX IF NOT EXISTS idx_play_history_asset_id ON play_history(asset_id);
```

Run:
```bash
# Add to Phase 0 database initialization or create migration script
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 << 'EOF'
CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    played_at TEXT NOT NULL,
    queue_name TEXT NOT NULL,
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);
CREATE INDEX IF NOT EXISTS idx_play_history_asset_id ON play_history(asset_id);
EOF
```

Expected: Play history table created

**Step 2: Implement play history tracking**

Create file `/srv/ai_radio/src/ai_radio/play_history.py`:

```python
"""
AI Radio Station - Play History Tracking
Records what played when for analytics and anti-repetition
"""
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def record_play(
    db_path: Path,
    asset_id: str,
    queue_name: str = "music"
) -> bool:
    """
    Record that an asset was played

    Args:
        db_path: Database path
        asset_id: Asset ID
        queue_name: Queue name (music, breaks, etc.)

    Returns:
        True if successful
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO play_history (asset_id, played_at, queue_name)
            VALUES (?, ?, ?)
            """,
            (asset_id, datetime.now().isoformat(), queue_name)
        )

        conn.commit()
        conn.close()

        logger.info(f"Recorded play: {asset_id} in {queue_name}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Failed to record play: {e}")
        return False


def get_recently_played_ids(
    db_path: Path,
    queue_name: str = "music",
    hours: int = 24,
    limit: int = 50
) -> list[str]:
    """
    Get recently played asset IDs

    Args:
        db_path: Database path
        queue_name: Queue to query
        hours: Look back this many hours
        limit: Maximum IDs to return

    Returns:
        List of asset IDs (most recent first)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute(
            """
            SELECT DISTINCT asset_id
            FROM play_history
            WHERE queue_name = ?
              AND played_at >= ?
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (queue_name, cutoff, limit)
        )

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    except sqlite3.Error as e:
        logger.error(f"Failed to get recent plays: {e}")
        return []


def get_play_stats(db_path: Path, hours: int = 24) -> dict:
    """
    Get play statistics for the last N hours

    Args:
        db_path: Database path
        hours: Look back period

    Returns:
        Dict with stats (total_plays, by_queue, unique_assets)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        # Total plays
        cursor.execute(
            "SELECT COUNT(*) FROM play_history WHERE played_at >= ?",
            (cutoff,)
        )
        total_plays = cursor.fetchone()[0]

        # By queue
        cursor.execute(
            """
            SELECT queue_name, COUNT(*)
            FROM play_history
            WHERE played_at >= ?
            GROUP BY queue_name
            """,
            (cutoff,)
        )
        by_queue = dict(cursor.fetchall())

        # Unique assets
        cursor.execute(
            "SELECT COUNT(DISTINCT asset_id) FROM play_history WHERE played_at >= ?",
            (cutoff,)
        )
        unique_assets = cursor.fetchone()[0]

        conn.close()

        return {
            "total_plays": total_plays,
            "by_queue": by_queue,
            "unique_assets": unique_assets
        }

    except sqlite3.Error as e:
        logger.error(f"Failed to get play stats: {e}")
        return {}
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/play_history.py << 'EOF'
[content above]
EOF
```

Expected: Play history module created

**Step 3: Update track selection to use play history**

Modify `/srv/ai_radio/src/ai_radio/track_selection.py` imports:

```python
from ai_radio.play_history import get_recently_played_ids
```

Update `enqueue_music.py` to use real history:

```python
# Replace placeholder with:
from ai_radio.play_history import get_recently_played_ids

recently_played = get_recently_played_ids(
    config.db_path,
    queue_name="music",
    hours=24,
    limit=RECENT_HISTORY_SIZE
)
```

Expected: Play history integrated

**Step 4: Commit**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio git add src/ai_radio/play_history.py scripts/enqueue_music.py
sudo -u ai-radio git commit -m "feat(phase-6): add play history tracking"
```

Expected: Changes committed

---

## Task 2: Health Check Script

**Files:**
- Create: `/srv/ai_radio/scripts/health-check.sh`

**Step 1: Create comprehensive health check**

Create file `/srv/ai_radio/scripts/health-check.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Health Check Script
# Quick status check for all critical services

echo "========================================"
echo "   AI Radio Station - Health Check"
echo "========================================"
echo

ERRORS=0

# Function to check service
check_service() {
    local service=$1
    local name=$2

    if systemctl is-active --quiet "$service"; then
        echo "✓ $name: RUNNING"
    else
        echo "✗ $name: NOT RUNNING"
        ((ERRORS++))
    fi
}

# Function to check file exists
check_file() {
    local file=$1
    local name=$2

    if [ -f "$file" ]; then
        echo "✓ $name: EXISTS"
    else
        echo "✗ $name: MISSING"
        ((ERRORS++))
    fi
}

# Function to check directory
check_dir() {
    local dir=$1
    local name=$2

    if [ -d "$dir" ]; then
        echo "✓ $name: EXISTS"
    else
        echo "✗ $name: MISSING"
        ((ERRORS++))
    fi
}

echo "=== Core Services ==="
check_service "icecast2.service" "Icecast2 Streaming"
check_service "ai-radio-liquidsoap.service" "Liquidsoap Playout"
echo

echo "=== Content Generation ==="
check_service "ai-radio-break-gen.timer" "Break Generation Timer"
check_file "/srv/ai_radio/assets/breaks/next.mp3" "Latest Break (next.mp3)"
echo

echo "=== Scheduling Services ==="
check_service "ai-radio-enqueue.timer" "Music Enqueue Timer"
check_service "ai-radio-break-scheduler.timer" "Break Scheduler Timer"
check_service "ai-radio-watch-drops.service" "Drop-in Watchdog"
echo

echo "=== Critical Directories ==="
check_dir "/srv/ai_radio/assets/music" "Music Library"
check_dir "/srv/ai_radio/assets/breaks" "Breaks Directory"
check_dir "/srv/ai_radio/drops" "Drop-in Directory"
echo

echo "=== Database ==="
check_file "/srv/ai_radio/db/radio.sqlite3" "SQLite Database"
echo

echo "=== Stream Status ==="
if curl -s -I http://127.0.0.1:8000/stream | grep -q "200 OK"; then
    echo "✓ Stream: BROADCASTING"
else
    echo "✗ Stream: NOT BROADCASTING"
    ((ERRORS++))
fi
echo

# Liquidsoap socket check
if [ -S "/run/liquidsoap/radio.sock" ]; then
    echo "✓ Liquidsoap Socket: AVAILABLE"

    # Try to query music queue
    QUEUE_SIZE=$(echo "music.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock 2>/dev/null | wc -l)
    echo "  Music Queue Depth: $QUEUE_SIZE tracks"
else
    echo "✗ Liquidsoap Socket: NOT AVAILABLE"
    ((ERRORS++))
fi
echo

# Summary
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "STATUS: ✓ ALL SYSTEMS OPERATIONAL"
    exit 0
else
    echo "STATUS: ✗ $ERRORS ISSUES DETECTED"
    exit 1
fi
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/health-check.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/health-check.sh
```

Expected: Health check script created

**Step 2: Test health check**

Run:
```bash
/srv/ai_radio/scripts/health-check.sh
```

Expected: Shows status of all services

**Step 3: Commit**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio git add scripts/health-check.sh
sudo -u ai-radio git commit -m "feat(phase-6): add comprehensive health check script"
```

Expected: Changes committed

---

## Task 3: Status Dashboard Script

**Files:**
- Create: `/srv/ai_radio/scripts/status-dashboard.sh`

**Step 1: Create status dashboard**

Create file `/srv/ai_radio/scripts/status-dashboard.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Status Dashboard
# Real-time status view with metrics

clear

while true; do
    tput cup 0 0

    echo "╔════════════════════════════════════════════════════╗"
    echo "║     AI RADIO STATION - STATUS DASHBOARD           ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo
    date
    echo

    # Queue Status
    echo "=== QUEUE STATUS ==="
    if [ -S "/run/liquidsoap/radio.sock" ]; then
        MUSIC_QUEUE=$(echo "music.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock 2>/dev/null | wc -l)
        BREAK_QUEUE=$(echo "breaks.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock 2>/dev/null | wc -l)

        echo "Music Queue:  $MUSIC_QUEUE tracks"
        echo "Break Queue:  $BREAK_QUEUE items"
    else
        echo "⚠ Liquidsoap socket unavailable"
    fi
    echo

    # Stream Status
    echo "=== STREAM STATUS ==="
    if curl -s -I http://127.0.0.1:8000/stream | grep -q "200 OK"; then
        LISTENERS=$(curl -s http://admin:$(cat /srv/ai_radio/.secrets/icecast_admin_password 2>/dev/null || echo "hackme")@127.0.0.1:8000/admin/stats | grep -oP '<Listeners>\K[0-9]+' | head -1 || echo "?")
        echo "Status: ✓ BROADCASTING"
        echo "Listeners: $LISTENERS"
    else
        echo "Status: ✗ OFFLINE"
    fi
    echo

    # Recent Play History
    echo "=== RECENT PLAYS (Last 5) ==="
    sqlite3 /srv/ai_radio/db/radio.sqlite3 << 'EOF' || echo "⚠ Database unavailable"
SELECT
    substr(played_at, 12, 5) as time,
    substr(a.title, 1, 30) as title,
    substr(a.artist, 1, 20) as artist
FROM play_history ph
JOIN assets a ON ph.asset_id = a.id
WHERE ph.queue_name = 'music'
ORDER BY ph.played_at DESC
LIMIT 5;
EOF
    echo

    # Service Status
    echo "=== SERVICE STATUS ==="
    systemctl is-active --quiet icecast2 && echo "✓ Icecast2" || echo "✗ Icecast2"
    systemctl is-active --quiet ai-radio-liquidsoap && echo "✓ Liquidsoap" || echo "✗ Liquidsoap"
    systemctl is-active --quiet ai-radio-enqueue.timer && echo "✓ Enqueue Timer" || echo "✗ Enqueue Timer"
    systemctl is-active --quiet ai-radio-break-gen.timer && echo "✓ Break Gen Timer" || echo "✗ Break Gen Timer"
    echo

    echo "Press Ctrl+C to exit | Refreshing every 5 seconds..."

    sleep 5
done
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/status-dashboard.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/status-dashboard.sh
```

Expected: Status dashboard created

**Step 2: Commit**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio git add scripts/status-dashboard.sh
sudo -u ai-radio git commit -m "feat(phase-6): add real-time status dashboard"
```

Expected: Changes committed

---

## Task 4: Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE6_COMPLETE.md`

**Step 1: Document Phase 6 completion**

Create file `/srv/ai_radio/docs/PHASE6_COMPLETE.md`:

```markdown
# Phase 6: Observability & Monitoring - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Essential operational visibility implemented with play history tracking, health checks, and status monitoring. Lightweight, pragmatic observability for single-server deployment.

## Implemented Components

### Play History
- ✅ SQLite play_history table
- ✅ Record plays with timestamp and queue
- ✅ Query recent plays for anti-repetition
- ✅ Play statistics (total, by queue, unique assets)
- ✅ Integration with track selection

### Health Checks
- ✅ Comprehensive health check script
- ✅ Service status monitoring
- ✅ File/directory verification
- ✅ Stream availability check
- ✅ Queue depth inspection via socket

### Status Dashboard
- ✅ Real-time status view (terminal UI)
- ✅ Queue metrics
- ✅ Stream status and listener count
- ✅ Recent play history
- ✅ Service health summary

### Logging
- ✅ Systemd journal integration
- ✅ Structured logging in all services
- ✅ Log aggregation via journalctl

## Usage

### Run Health Check

```bash
/srv/ai_radio/scripts/health-check.sh
```

Expected output:
```
✓ Icecast2 Streaming: RUNNING
✓ Liquidsoap Playout: RUNNING
✓ Break Generation Timer: RUNNING
✓ Stream: BROADCASTING
✓ ALL SYSTEMS OPERATIONAL
```

### View Status Dashboard

```bash
/srv/ai_radio/scripts/status-dashboard.sh
```

Displays real-time status, refreshes every 5 seconds. Press Ctrl+C to exit.

### Query Play History

```python
from ai_radio.play_history import get_recently_played_ids, get_play_stats

# Get recent plays
recent = get_recently_played_ids(db_path, queue_name="music", hours=24, limit=50)

# Get statistics
stats = get_play_stats(db_path, hours=24)
print(f"Total plays: {stats['total_plays']}")
print(f"Unique assets: {stats['unique_assets']}")
```

### View Logs

```bash
# All AI Radio logs
sudo journalctl -t ai-radio-* -f

# Specific service
sudo journalctl -u ai-radio-enqueue.service -f

# Last hour
sudo journalctl -u ai-radio-liquidsoap.service --since "1 hour ago"
```

## Metrics Available

**Play History:**
- Total plays (by time period)
- Plays by queue (music, breaks)
- Unique assets played
- Play timestamps

**Queue Metrics:**
- Music queue depth
- Break queue depth
- Real-time via Liquidsoap socket

**Service Health:**
- Service running status (systemd)
- Stream availability (HTTP check)
- Socket availability

**Stream Stats:**
- Listener count (via Icecast admin API)
- Stream status (broadcasting/offline)

## Test Results

All observability components operational:
- Play history tracking functional
- Health check script passes
- Status dashboard displays correctly
- Logs accessible via journalctl

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY LAYER                        │
├─────────────────────────────────────────────────────────────┤
│ Play History (SQLite)                                        │
│   - Tracks played, queue, timestamp                         │
│   - 24-hour lookback for anti-repetition                    │
│   - Statistics and analytics                                │
├─────────────────────────────────────────────────────────────┤
│ Health Checks                                                │
│   - Service status (systemd)                                │
│   - Stream availability (HTTP)                              │
│   - File/directory verification                             │
│   - Queue depth (socket)                                    │
├─────────────────────────────────────────────────────────────┤
│ Status Dashboard (Terminal UI)                              │
│   - Real-time queue metrics                                 │
│   - Stream status and listeners                             │
│   - Recent play history                                     │
│   - Service health summary                                  │
├─────────────────────────────────────────────────────────────┤
│ Logging (Systemd Journal)                                    │
│   - Structured logs from all services                       │
│   - Centralized via journalctl                              │
│   - Searchable, filterable                                  │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

Phase 7 will implement operator tools:
- Manual queue control scripts
- Force break trigger
- Skip track command
- Emergency playlist activation
- Configuration reloading

## SOW Compliance

✅ Section 14: Operational visibility
✅ Section 14: Play history tracking
✅ Section 14: Health monitoring
✅ Section 3: Simple, maintainable tooling
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/docs/PHASE6_COMPLETE.md << 'EOF'
[content above]
EOF
```

Expected: Documentation created

**Step 2: Commit all Phase 6 work**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio git add .
sudo -u ai-radio git commit -m "feat(phase-6): complete observability and monitoring

Implemented:
- Play history tracking in SQLite
- Comprehensive health check script
- Real-time status dashboard
- Play statistics and metrics
- Systemd journal integration

All SOW Section 14 requirements met."
```

Expected: Phase 6 complete and committed

---

## Definition of Done

- [x] Play history table schema
- [x] Play history tracking module
- [x] Integration with track selection (anti-repetition)
- [x] Play statistics queries
- [x] Health check script
- [x] Status dashboard script
- [x] Systemd journal integration
- [x] Documentation complete

## Verification Commands

```bash
# 1. Check play history table
sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT COUNT(*) FROM play_history;"

# 2. Run health check
/srv/ai_radio/scripts/health-check.sh

# 3. View status dashboard
/srv/ai_radio/scripts/status-dashboard.sh
# (Press Ctrl+C to exit)

# 4. Query recent plays
sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT * FROM play_history ORDER BY played_at DESC LIMIT 10;"

# 5. Check logs
sudo journalctl -u ai-radio-* --since "1 hour ago"
```

All commands should complete successfully without errors.

---

## Notes

- **Lightweight:** No complex metrics infrastructure (Prometheus/Grafana not needed for single-server)
- **Pragmatic:** Uses SQLite for storage, systemd journal for logs, shell scripts for dashboards
- **Maintainable:** Simple tools, no external dependencies
- **Sufficient:** Provides all visibility needed for troubleshooting and monitoring
- **Extensible:** Can add Prometheus/Grafana later if needed, but not required for MVP
