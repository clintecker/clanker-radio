# Phase 5: Scheduling & Orchestration - Validation Results

**Date:** 2025-12-18
**Validator:** Gemini-3-Pro (via PAL MCP codereview)
**Status:** 🔴 CRITICAL ISSUES FOUND

## Executive Summary

Phase 5 provides solid scheduling logic for the station, but **systemd timer configuration is critically flawed**. Using `OnUnitActiveSec` for the break scheduler will almost certainly result in the station missing its hourly news slots entirely. With timer fixes, response parsing corrections, and anti-repetition implementation, this phase will be production-ready.

**Risk Assessment:**
- **Deployment Blocker:** Timer drift will cause station to miss scheduled breaks
- **Operational Risk:** Double-scheduling race condition
- **Technical Debt:** Missing SOW-mandated anti-repetition logic

---

## Issues Found

### 🔴 CRITICAL (3 issues)

#### Issue 1: Systemd Timer Drift Causing Missed Breaks
**Location:** `ai-radio-break-scheduler.timer`
**Line:** Task 5, Step 4, lines 889-907

**Problem:**
The plan uses `OnUnitActiveSec=5min` relative to boot time (`OnBootSec=2min`). This creates a floating interval that is not aligned with the wall clock.

**Scenario:**
- If VM boots at 10:07, timer runs at 10:09, 10:14, 10:19...
- Timer will NEVER land in the 00-05 minute window required by `schedule_break.py`
- **The station will never play scheduled breaks**

**SOW Impact:**
- Violates SOW Section 11: "hourly news/weather breaks"
- Breaks main requirement of the system

**Fix:**
Use `OnCalendar` for deterministic wall-clock alignment:

```ini
[Timer]
# Run every 5 minutes aligned to the hour (00, 05, 10, 15, 20...)
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```

**Validation:**
```bash
# Verify timer triggers at correct wall-clock times
sudo systemctl list-timers ai-radio-break-scheduler.timer
# Should show next trigger at :00, :05, :10, etc.
```

---

#### Issue 2: Break Double-Scheduling Race Condition
**Location:** `scripts/schedule_break.py`
**Line:** Task 4, Step 1, line 705

**Problem:**
The logic `if minutes > 5: ... skipping` allows execution at minutes 0, 1, 2, 3, 4, and **5**.

If the timer runs at 10:00 and 10:05 (which `OnCalendar` would guarantee), the script will push a break **twice** in the same hour.

**Fix (Option A - Tighten Window):**
```python
# Change line 705 from:
if minutes > 5:

# To:
if minutes >= 5:  # Exclude minute 5
    logger.info(f"Not near top of hour (minute: {minutes}), skipping")
    sys.exit(0)
```

**Fix (Option B - Idempotency Check - RECOMMENDED):**
```python
# After line 711, add queue check:
# Find next.mp3 (SOW-mandated file)
next_break = BREAKS_DIR / "next.mp3"

# CHECK: Don't double-schedule
client = LiquidsoapClient()
if client.get_queue_length(QUEUE_NAME) > 0:
    logger.info("Break already queued, skipping")
    sys.exit(0)

if not next_break.exists():
    # ... rest of existing logic
```

---

#### Issue 3: Liquidsoap Response Parsing Bug
**Location:** `src/ai_radio/liquidsoap_client.py`
**Line:** Task 1, Step 3, line 178

**Problem:**
Liquidsoap's Telnet/Socket interface typically ends responses with an `END` line. The current parsing counts this as a queue item, leading to off-by-one errors:
- Reports 1 track when empty
- Reports 3 when actually 2

**Impact:**
- `enqueue_music.py` will think queue is fuller than it is
- May under-fill queue, causing dead air

**Fix:**
```python
# Change lines 177-179 from:
# Parse response - format is typically a list of items
# Count non-empty lines
lines = [line.strip() for line in response.split('\n') if line.strip()]

# To:
# Parse response - format is typically a list of items
# Count non-empty lines (filter out protocol END marker)
lines = [
    line.strip()
    for line in response.split('\n')
    if line.strip() and line.strip() != "END"
]
```

---

### 🟠 HIGH (2 issues)

#### Issue 4: Missing Anti-Repetition Implementation
**Location:** `scripts/enqueue_music.py`
**Line:** Task 3, Step 1, lines 538-554

**Problem:**
The plan leaves `get_recently_played_ids` as a placeholder returning empty list (`return []`).

**SOW Impact:**
- SOW Section 13 explicitly requires anti-repetition logic
- Launching without this means the station will randomly repeat tracks back-to-back
- Contract non-compliance

**Fix:**
Implement the query against the `play_history` table defined in SOW Section 6:

```python
def get_recently_played_ids(db_path: Path, count: int = RECENT_HISTORY_SIZE) -> list[str]:
    """
    Get IDs of recently played tracks from play_history table

    Args:
        db_path: Database path
        count: Number of recent IDs to fetch

    Returns:
        List of track IDs
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch last N asset_ids from play_history (SOW Section 6)
        cursor.execute(
            """
            SELECT asset_id
            FROM play_history
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (count,)
        )

        ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        return ids

    except sqlite3.Error as e:
        logger.warning(f"Failed to fetch play history: {e}")
        return []  # Graceful degradation
    except Exception as e:
        logger.error(f"Unexpected error fetching history: {e}")
        return []
```

**Note:**
Phase 6 implements the *writing* to `play_history` table. Phase 5 must be able to *read* it (even if empty initially).

---

#### Issue 5: Enqueue Service Execution Path (PYTHONPATH)
**Location:** `ai-radio-enqueue.service`
**Line:** Task 5, Step 1, line 801

**Problem:**
The service uses `ExecStart=/srv/ai_radio/.venv/bin/python ...` but `scripts/enqueue_music.py` relies on `sys.path.insert` to find the `ai_radio` package. This is fragile in production.

**Fix:**
Add `PYTHONPATH` environment variable to systemd unit:

```ini
[Service]
Type=oneshot
User=ai-radio
Group=ai-radio
WorkingDirectory=/srv/ai_radio

# Add this line:
Environment="PYTHONPATH=/srv/ai_radio/src"

ExecStart=/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/enqueue_music.py
```

**Alternative Fix:**
Apply to BOTH `ai-radio-enqueue.service` AND `ai-radio-break-scheduler.service`.

---

### 🟡 MEDIUM (1 issue)

#### Issue 6: Break Generation Timing Alignment
**Location:** Overall architecture
**Context:** Phase 4 + Phase 5 coordination

**Observation:**
- SOW requires breaks to be "fully rendered to disk ≥ 10 minutes before scheduled play"
- Phase 5 `schedule_break.py` pushes `next.mp3` at top of hour (`:00`)
- Phase 4 `news_gen` runs every 10 minutes

**Validation Needed:**
Verify that Phase 4's `ai-radio-break-gen.timer` generates breaks BEFORE scheduler picks them up.

**Recommendation:**
Update Phase 4's timer to align generation at `:50` each hour:

```ini
[Timer]
# Run at 50 minutes past each hour (10 min before scheduled play)
OnCalendar=*:50
```

This ensures `next.mp3` is ready at `:50`, satisfying the "10 minutes before `:00` play time" requirement.

**Note:** This is architectural coordination, not a Phase 5 bug, but should be verified during integration.

---

## Positive Aspects

✅ **Energy-Aware Architecture:** The `track_selection.py` implementation of "wave" patterns is sophisticated and adds significant production value

✅ **Producer/Consumer Safety:** Strict separation between Python decision-making and Liquidsoap execution. If Python crashes, Liquidsoap keeps playing the buffer

✅ **Fallback Logic:** The scheduler explicitly checks `next.mp3` and falls back to `last_good.mp3`, strictly adhering to SOW reliability requirements

✅ **Resource Isolation:** CPU nice level 10 prevents starving Liquidsoap during intensive operations

✅ **SOW Section 6 Compliance:** Uses correct schema (`kind`, `duration_sec`)

---

## Recommended Fixes Priority

### Must Fix Before Deployment (CRITICAL):

1. **Change Systemd Timers:** Update `ai-radio-break-scheduler.timer` to use `OnCalendar=*:0/5` to guarantee execution at wall-clock times
2. **Fix Liquidsoap Parsing:** Filter out `"END"` from `liquidsoap_client.py` response parsing
3. **Add Break Idempotency:** Implement Option B (queue check) to prevent double-scheduling

### Must Fix Before Launch (HIGH):

4. **Implement History Read:** Replace placeholder `get_recently_played_ids` with real SQL query
5. **Add PYTHONPATH:** Add `Environment="PYTHONPATH=/srv/ai_radio/src"` to both service units

### Should Fix (MEDIUM):

6. **Verify Phase 4 Timing:** Ensure break generation runs at `:50` to satisfy "10 minutes before" requirement

---

## Top 3 Fixes (Quick Win)

1. **systemd Timer Fix** (5 minutes)
   - Change `OnUnitActiveSec=5min` → `OnCalendar=*:0/5`
   - Apply to `ai-radio-break-scheduler.timer`

2. **Liquidsoap Parsing Fix** (2 minutes)
   - Add `and line.strip() != "END"` to filter condition
   - Location: `liquidsoap_client.py:178`

3. **Implement History Query** (10 minutes)
   - Replace placeholder with SELECT query
   - Location: `enqueue_music.py:538-554`

**Total time to fix critical issues: ~20 minutes**

---

## SOW Compliance

✅ Section 11: Multi-level fallback chain (music + breaks)
⚠️  Section 11: Break insertion at top of hour (timer fix required)
✅ Section 13: Energy-aware track selection
⚠️  Section 13: Anti-repetition logic (implementation required)
✅ Section 9: next.mp3 / last_good.mp3 rotation
✅ Section 3: Producer/consumer separation

---

## Summary

**Overall Assessment:** Phase 5 provides solid scheduling logic with excellent energy-aware track selection and proper producer/consumer separation. However, **systemd timer misconfiguration will prevent scheduled breaks from playing** - this is a deployment blocker.

**Deployment Readiness:** 🔴 **NOT READY** - Critical timer fix required

**After Fixes Applied:** 🟢 **READY FOR DEPLOYMENT**

---

## Validation Checklist

After applying fixes, verify:

- [ ] `sudo systemctl list-timers | grep break-scheduler` shows next trigger at `:00`, `:05`, `:10`, etc.
- [ ] `echo "music.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock` shows correct count (not off-by-one)
- [ ] `get_recently_played_ids()` returns list of recent asset IDs from database
- [ ] Break plays at top of hour without duplication
- [ ] Unit tests pass: `pytest tests/test_liquidsoap_client.py tests/test_track_selection.py -v`

---

**Validator Notes:**
This review focuses on the integration between scheduling services and Liquidsoap, ensuring wall-clock timing alignment and SOW compliance for break scheduling. The core logic is sound; fixes are primarily operational configuration issues.
