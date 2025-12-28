# Now Playing System - Fixes Applied

## Summary

Fixed critical bugs causing incorrect metadata display after station IDs and news breaks, and optimized the system for more real-time updates.

## Problems Identified

### 1. SQL Query Bug (Critical)
**Location:** `scripts/export_now_playing.py:586`

**Problem:** Query used `WHERE a.path = ?` after LEFT JOIN with assets table. Station IDs and breaks aren't in the assets table, so `a.path` was NULL and the WHERE clause failed, returning zero rows.

**Impact:**
- Export script fabricated metadata with wrong timestamps
- Missing asset_ids caused frontend track detection to fail
- Progress bars showed incorrect timing
- Display appeared "stuck" on station ID metadata

### 2. Race Conditions
**Location:** Multiple systemd timers running simultaneously

**Problem:**
- `ai-radio-export-nowplaying.timer` ran every 10 seconds
- `record_play.py` also triggered exports immediately
- Both could run simultaneously, causing inconsistent state

**Impact:**
- Duplicate exports with different timestamps
- Database queries racing with writes
- Unpredictable metadata updates

### 3. Polling Latency
**Location:** `nginx/index.html:505`

**Problem:** Frontend polled every 5 seconds, combined with 10-second timer meant up to 15s lag

**Impact:**
- Short tracks (3-5s station IDs) could be missed entirely
- Slow response to track changes
- Poor user experience

## Fixes Applied

### Fix 1: Corrected SQL Query ✅ (Updated after code review)

**File:** `scripts/export_now_playing.py`

**Changes:**
1. Added `filename_stem` calculation to extract asset_id for non-music tracks
2. Changed WHERE clause with **tighter time windows** to prevent matching old plays:
   ```sql
   WHERE (
       (a.path = ? AND ph.played_at >= datetime('now', '-10 minutes'))
       OR
       (ph.asset_id = ? AND ph.played_at >= datetime('now', '-30 seconds')
        AND ph.source IN ('break', 'bumper'))
   )
   ```
   - Music tracks: 10-minute window (normal)
   - Station IDs/breaks: **30-second window** (prevents matching old plays of same asset_id)
3. Fixed artist logic to use `config.station_name` for breaks/bumpers
4. Updated query parameters to include station name and filename stem
5. **Added 100ms sleep buffer** for non-music tracks to allow database write to complete

**Code:**
```python
# Line 573-617 (simplified for clarity)
filename_stem = os.path.splitext(os.path.basename(filename))[0]

# For non-music tracks, give database write time to complete
if source_type in ("break", "bumper"):
    import time
    time.sleep(0.1)  # 100ms buffer

cursor.execute(
    """
    SELECT
        ph.asset_id,
        COALESCE(a.title,
            CASE
                WHEN ph.source = 'break' THEN 'News Break'
                WHEN ph.source = 'bumper' THEN 'Station Identification'
                ELSE 'Unknown'
            END
        ) as title,
        COALESCE(a.artist,
            CASE
                WHEN ph.source IN ('break', 'bumper') THEN ?
                ELSE 'Clint Ecker'
            END
        ) as artist,
        a.album,
        a.duration_sec,
        ph.played_at,
        ph.source
    FROM play_history ph
    LEFT JOIN assets a ON ph.asset_id = a.id
    WHERE (
        (a.path = ? AND ph.played_at >= datetime('now', '-10 minutes'))
        OR
        (ph.asset_id = ? AND ph.played_at >= datetime('now', '-30 seconds')
         AND ph.source IN ('break', 'bumper'))
    )
    ORDER BY ph.played_at DESC
    LIMIT 1
    """,
    (config.station_name, filename, filename_stem)
)
```

**Also fixed fallback query at line 510-539** with same artist logic improvement.

### Fix 2: Timer as Fallback ✅ (Changed after code review)

**File:** `systemd/ai-radio-export-nowplaying.timer`

**Changes:**
- Changed from 10-second interval to **2-minute fallback**
- Timer now runs every 2 minutes as safety net
- Primary exports still triggered immediately by `record_play.py`

**Rationale:**
- Triggered exports provide immediate updates (100-200ms)
- 2-minute fallback catches failures without racing with triggered exports
- Provides resilience if `record_play.py` crashes or fails to trigger
- Much longer interval (2min vs 10s) prevents race conditions

### Fix 3: Optimized Frontend Polling ✅

**File:** `nginx/index.html:505`

**Changes:**
- Reduced `UPDATE_INTERVAL` from 5000ms (5s) to 2000ms (2s)

**Rationale:**
- Catches track changes faster (2s vs 5s)
- Better UX for short tracks
- Still efficient (not excessive polling)
- Complements the immediate exports from backend

## How It Works Now

### Data Flow After Fixes

```
1. Station ID starts playing (T0)
   ↓
2. Liquidsoap callback fires → record_play.py
   ↓
3. record_play.py writes to play_history (T0 + 50-100ms)
   - Correct asset_id: "station_id_5"
   - Accurate timestamp from database
   ↓
4. record_play.py triggers export_now_playing.py (T0 + 100ms)
   ↓
5. export_now_playing.py runs FIXED query
   - Matches ph.asset_id = "station_id_5" ✓
   - Returns actual play_history record ✓
   - Uses correct timestamp ✓
   ↓
6. JSON written with accurate metadata (T0 + 200-300ms)
   ↓
7. Frontend polls at T0 + 2s (or earlier if already in cycle)
   - Sees accurate metadata
   - Progress bar starts from correct time
   - Display updates properly
```

### Key Improvements

1. **Correctness:** Query now finds station IDs/breaks in play_history
2. **Accuracy:** Uses real timestamps from database, not fabricated ones
3. **Speed:** Immediate export trigger + 2s polling = max 2s lag
4. **Reliability:** No more race conditions from dual timers
5. **Consistency:** Data matches across all track types

## Testing Recommendations

### Manual Test Procedure

1. **Start the radio:**
   ```bash
   systemctl start ai-radio-liquidsoap
   ```

2. **Stop the disabled timer** (if it was running):
   ```bash
   systemctl stop ai-radio-export-nowplaying.timer
   systemctl disable ai-radio-export-nowplaying.timer
   ```

3. **Wait for station ID** (plays at :15, :30, :45 past the hour):
   - Watch frontend display
   - Check that station ID shows correctly
   - Verify progress bar moves accurately
   - Confirm it transitions smoothly to next music track

4. **Check the logs:**
   ```bash
   tail -f /srv/ai_radio/logs/liquidsoap.log
   journalctl -u ai-radio-export-nowplaying -f
   ```

5. **Verify database:**
   ```bash
   sqlite3 ~/.config/ai_radio/radio.db \
     "SELECT asset_id, title, source, played_at FROM play_history ORDER BY played_at DESC LIMIT 5"
   ```

### Expected Results

✅ Station ID appears in display within 2 seconds of starting
✅ Progress bar shows accurate timing
✅ asset_id is populated (not NULL)
✅ Timestamp matches actual play time
✅ Smooth transition to next music track
✅ No "stuck" metadata
✅ No duplicate/conflicting exports in logs

### What to Watch For

❌ If display still shows wrong metadata:
- Check that timer is actually disabled: `systemctl status ai-radio-export-nowplaying.timer`
- Verify export script is using new code: `grep -n "filename_stem" scripts/export_now_playing.py`

❌ If progress bar is still wrong:
- Check JSON file timestamp: `cat /srv/ai_radio/public/now_playing.json | jq .current.played_at`
- Compare with database: `sqlite3 ... "SELECT played_at FROM play_history WHERE asset_id='station_id_5'"`

❌ If transitions are slow:
- Verify frontend is using 2s interval: View source in browser, check UPDATE_INTERVAL

## Performance Impact

### Before Fixes
- Export runs: Every 10s (timer) + on track change (trigger) = 2 exports per track minimum
- SQL queries: Failed for station IDs, caused expensive ffprobe fallback
- Frontend polls: Every 5s
- Total latency: Up to 15 seconds

### After Fixes
- Export runs: Only on track change = 1 export per track
- SQL queries: Succeed for all track types, no fallback needed
- Frontend polls: Every 2s
- Total latency: Max 2-3 seconds

**Result:** ~5x faster updates, ~50% fewer exports, no wasted CPU on failed queries

## Future Enhancements (Optional)

### Phase 3: Real-Time Push Updates

For even more responsive updates, consider implementing Server-Sent Events (SSE) or WebSocket:

**Approach:**
1. Add SSE endpoint to serve now_playing updates
2. Have export_now_playing.py notify SSE server when JSON updates
3. Frontend subscribes to SSE stream instead of polling
4. Updates arrive in <100ms instead of up to 2s

**Benefits:**
- Sub-second latency
- No polling overhead
- Instant track changes
- Better for mobile/battery

**Trade-offs:**
- More complex implementation
- Requires keeping connections open
- May need nginx configuration changes

## Files Modified

1. `scripts/export_now_playing.py` - Fixed SQL queries (2 locations)
2. `systemd/ai-radio-export-nowplaying.timer` - Disabled timer
3. `nginx/index.html` - Reduced polling interval
4. `docs/now_playing_sequence_diagram.md` - Added sequence diagrams (new)
5. `docs/FIXES_APPLIED.md` - This document (new)

## Code Review Findings

After initial implementation, a thorough code review identified several critical issues that have been addressed:

### Critical Issues Fixed

1. **SQL Query Logic Flaw**: Original fix used `WHERE (a.path = ? OR ph.asset_id = ?)` which could match OLD plays of the same asset_id within the 10-minute window. Fixed by using a 30-second window for non-music tracks.

2. **Race Condition**: Export process runs asynchronously and could query database before write completes. Fixed by adding 100ms sleep buffer for non-music tracks.

3. **Timer Disabled Completely**: Removing timer entirely left no resilience if triggered exports fail. Fixed by keeping timer as 2-minute fallback.

### Known Limitations

- **Frontend Polling**: 2-second polling still has some latency for very short tracks (could be improved with Server-Sent Events)
- **Test Coverage**: Integration tests not yet written (recommended before production deployment)
- **30-Second Window**: Very rapid repeated plays of same station ID could theoretically fail (unlikely in practice)

### Future Improvements

1. **Server-Sent Events (SSE)** for real-time push updates (sub-second latency)
2. **Adaptive Frontend Polling** that increases frequency near track boundaries
3. **Integration Tests** for SQL query logic with various track types
4. **Database WAL Mode** optimization for better concurrent access

## Post-Deployment Fixes (2025-12-28)

After initial deployment, we discovered two additional issues:

### Issue 4: Triggered Exports Not Working

**Problem**: File ownership prevented triggered exports from running. Scripts were owned by deployment user instead of `ai-radio` user.

**Symptom**: Station IDs and track changes only updated via 2-minute fallback timer, causing up to 2-minute delays in metadata updates.

**Root Cause**: Deployment script copies files correctly but in one instance, ownership was not set properly.

**Fix**: Ensured deployment script sets correct ownership:
```bash
sudo chown ai-radio:ai-radio /srv/ai_radio/scripts/*.py
```

**Verification**: The `deploy_scripts()` function already includes this step (line 139), but should be verified after each deployment.

### Issue 5: Station ID Duration Showing as Null

**Problem**: Station IDs showed `duration_sec: null`, causing frontend playhead to display "00:00 / 00:00".

**Root Cause**: When fallback timer runs ~50 seconds after station ID starts:
1. SQL query finds station ID in play_history (within 30-second window initially)
2. But Liquidsoap has moved to next music track
3. Code checked `source_type` from NEW Liquidsoap metadata (music)
4. Didn't call ffprobe because source_type != "bumper"

**Fix Applied** (scripts/export_now_playing.py:630-637):
- Use `row_source` from database instead of `source_type` from Liquidsoap
- This ensures duration is calculated based on the ACTUAL play record, not current stream state

```python
row_source = row[6]  # Source from database (accurate for this play record)

if duration_sec is None and row_source in ("break", "bumper") and filename:
    logger.info(f"Getting duration for {row_source} from file: {filename}")
    duration_sec = get_duration_from_file(filename)
```

**Impact**: Station IDs and breaks now show correct duration and playhead progress.

## Related Issues

- Issue #1: Station ID playback causes queue rewind and stuck now_playing metadata ✅
- Issue #5: now_playing.json causes display issues after station IDs and breaks ✅

Both issues should be resolved by these fixes.
