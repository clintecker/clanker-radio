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

### Fix 1: Corrected SQL Query ✅

**File:** `scripts/export_now_playing.py`

**Changes:**
1. Added `filename_stem` calculation to extract asset_id for non-music tracks
2. Changed WHERE clause from:
   ```sql
   WHERE a.path = ?
   ```
   To:
   ```sql
   WHERE (a.path = ? OR ph.asset_id = ?)
   ```
3. Fixed artist logic to use `config.station_name` for breaks/bumpers
4. Updated query parameters to include station name and filename stem

**Code:**
```python
# Line 567-601
filename_stem = os.path.splitext(os.path.basename(filename))[0]

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
    WHERE (a.path = ? OR ph.asset_id = ?)
      AND ph.played_at >= datetime('now', '-10 minutes')
    ORDER BY ph.played_at DESC
    LIMIT 1
    """,
    (config.station_name, filename, filename_stem)
)
```

**Also fixed fallback query at line 510-539** with same artist logic improvement.

### Fix 2: Disabled Systemd Timer ✅

**File:** `systemd/ai-radio-export-nowplaying.timer`

**Changes:**
- Commented out entire timer configuration
- Added explanation of why it's disabled
- Kept file for reference/debugging

**Rationale:**
- Triggered exports from `record_play.py` provide immediate updates
- Eliminates race conditions
- Reduces unnecessary system load
- More reliable than periodic polling

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

## Related Issues

- Issue #1: Station ID playback causes queue rewind and stuck now_playing metadata
- Issue #5: now_playing.json causes display issues after station IDs and breaks

Both issues should be resolved by these fixes.
