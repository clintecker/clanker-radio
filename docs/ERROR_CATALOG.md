# Error Catalog - 2025-12-29

## Critical Issues

### 1. SSE Push Updates Not Broadcasting on Track Changes ✅ FULLY RESOLVED
**Service:** ai-radio-push.service + ai-radio-liquidsoap.service
**Status:** ✅ WORKING - Real-time updates with <1s latency
**Original Error:** File watch not triggering on atomic renames
**Impact:** Frontend not receiving real-time updates via SSE

**Root Causes Identified:**
1. `PrivateTmp=yes` isolated both /tmp and /var/tmp (subprocess logs invisible)
2. Subprocess spawning from record_play.py was complex and unreliable
3. `ProtectSystem=strict` made /srv read-only
4. `ReadWritePaths` didn't include /srv/ai_radio/public

**Fixes Applied:**
1. Eliminated subprocess spawning - call export_now_playing() directly from record_play.py
2. Added /srv/ai_radio/public to ReadWritePaths in liquidsoap service
3. Simplified architecture: callback → direct function call → JSON write → HTTP POST → SSE broadcast

**Verification:** Track change at 18:49:36 → SSE broadcast at 18:49:37 (<1 second)
**Resolution Date:** 2025-12-29 18:50

### 2. ai-radio-break-gen.service - News Break Generation Failed
**Service:** ai-radio-break-gen.service
**Status:** ● FAILED
**Last Failure:** Dec 29 17:36:32
**Error:**
```
AttributeError: 'RadioConfig' object has no attribute 'hallucination_chance'
  File "/srv/ai_radio/src/ai_radio/news.py", line 296, in fetch_headlines
    if random.random() < config.hallucination_chance:
```
**Impact:** No news breaks being generated (top-of-hour breaks missing)
**Root Cause:** Missing config attribute `hallucination_chance` in RadioConfig Pydantic model
**Fix:** Add `hallucination_chance` field to config or remove the feature

### 3. ai-radio-station-id.service - Station ID Enqueue Failed
**Service:** ai-radio-station-id.service
**Status:** ● FAILED
**Last Failure:** Dec 29 17:30:20
**Error:** Exit code 1 (detailed logs needed)
**Impact:** Station IDs not being queued at :15, :30, :45 marks
**Root Cause:** Unknown - needs log investigation
**Fix:** Investigate logs with: `sudo journalctl -u ai-radio-station-id.service -n 50`

### 4. ai-radio-schedule-station-id.service - Station ID Scheduler Killed
**Service:** ai-radio-schedule-station-id.service
**Status:** ● FAILED
**Last Failure:** Dec 23 03:13:00
**Error:** Main process killed by SIGTERM
**Impact:** Station ID scheduling not working
**Root Cause:** Process killed (possibly manual stop or system restart)
**Fix:** Check service definition, restart service

### 5. ai-radio-watch-drops.service - Drop-in File Watchdog Failed
**Service:** ai-radio-watch-drops.service
**Status:** ● FAILED
**Last Failure:** Dec 20 23:44:02
**Error:** Dependency failed
**Impact:** Drop-in files (manual audio drops) not being processed
**Root Cause:** Service depends on another service that's not running
**Fix:** Identify dependency chain: `systemctl list-dependencies ai-radio-watch-drops.service`

## Working Services

- ✅ ai-radio-push.service - Running (testing change detection)
- ✅ ai-radio-liquidsoap.service - Running
- ✅ ai-radio-liquidsoap-fallback.service - Running
- ✅ ai-radio-dj-tag-api.service - Running
- ✅ ai-radio-break-gen.timer - Active (but service fails)
- ✅ ai-radio-enqueue.timer - Active
- ✅ ai-radio-export-nowplaying.timer - Active (fallback for SSE)
- ✅ ai-radio-station-id.timer - Active (but service fails)

## Non-Critical Issues

### Browser Tab Throttling (Solved)
**Issue:** Frontend polling throttled to 1 minute when tab in background
**Solution:** Implemented SSE push for real-time updates
**Status:** ✅ DEPLOYED

### Stream Stats Showing Wrong Bitrate (Solved)
**Issue:** Frontend always showed 192kbps stats even when 128kbps selected
**Solution:** Track `currentBitrate` and find matching stream in `stream.source[]`
**Status:** ✅ DEPLOYED

### Cloudflare/Nginx Caching Delays (Solved)
**Issue:** `Cache-Control: max-age=5` caused stale data
**Solution:** Set `Cache-Control: no-store, no-cache, must-revalidate` + SSE bypass
**Status:** ✅ DEPLOYED

## System Architecture Notes

### Current Update Flow
```
Track Change (Liquidsoap)
    ↓
record_play.py (callback)
    ↓
trigger_export() (subprocess.Popen)
    ↓
export_now_playing.py (writes JSON)
    ↓
os.rename(tempfile, now_playing.json)  ← ATOMIC WRITE
    ↓
[SSE Daemon should detect here] ← CURRENTLY BROKEN
    ↓
Broadcast to connected clients
    ↓
Frontend (EventSource)
```

### Proposed Fix: Direct Notification
```
export_now_playing.py
    ↓
Write JSON (as before)
    ↓
HTTP POST localhost:8001/notify  ← NEW
    ↓
SSE Daemon broadcasts immediately
```

## Service Dependencies

```
ai-radio-liquidsoap.service
    ↓
Calls: record_play.py, enqueue scripts

ai-radio-push.service
    ← Watches: now_playing.json

ai-radio-break-gen.timer
    → Triggers: ai-radio-break-gen.service

ai-radio-station-id.timer
    → Triggers: ai-radio-station-id.service
```

## Next Steps Priority

1. **HIGH:** Verify SSE directory watch works (track change at ~17:39)
2. **HIGH:** Fix break-gen config error (breaks not generating)
3. **MEDIUM:** Implement direct SSE notification (if watch fails)
4. **MEDIUM:** Fix station-id services (IDs not playing)
5. **LOW:** Fix watch-drops dependency
