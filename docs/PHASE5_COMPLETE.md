# Phase 5: Scheduling & Orchestration - Complete

**Date:** 2025-12-19
**Status:** ✅ Complete

## Summary

Automated scheduling and orchestration system is fully operational. Services maintain music queue depth, select tracks with energy awareness, and schedule breaks at top of hour.

## Implemented Components

### Music Queue Management
- ✅ Liquidsoap Unix socket client
- ✅ Queue depth monitoring
- ✅ Automatic filling to target depth (20 tracks)
- ✅ Minimum threshold (10 tracks)
- ✅ Track push via socket

### Energy-Aware Selection
- ✅ Energy-level based track selection
- ✅ Flow patterns (wave, ascending, descending, mixed)
- ✅ Anti-repetition logic (recent history exclusion)
- ✅ Random selection within energy bands

### Break Scheduling
- ✅ Top-of-hour detection (within 5 minutes)
- ✅ next.mp3 / last_good.mp3 SOW-compliant selection
- ✅ Automatic fallback to last_good.mp3
- ✅ Push to break queue

### Systemd Timers
- ✅ Music enqueue timer (every 5 minutes)
- ✅ Break scheduler timer (every 5 minutes, wall-clock aligned)
- ✅ CPU nice level (10) for resource isolation
- ✅ Persistent timers (catch up after downtime)

## Usage

### Manual Queue Management

```bash
# Run enqueue service manually
sudo systemctl start ai-radio-enqueue.service

# Check logs
sudo journalctl -u ai-radio-enqueue.service -f

# Check timer status
sudo systemctl status ai-radio-enqueue.timer
```

### Manual Break Scheduling

```bash
# Run break scheduler manually
sudo systemctl start ai-radio-break-scheduler.service

# Check logs
sudo journalctl -u ai-radio-break-scheduler.service -f
```

### Check Queue Status via Socket

```bash
# Connect to Liquidsoap socket
echo "music.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock

# Check break queue
echo "breaks.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock
```

## Configuration

### Queue Depth Settings

Edit `scripts/enqueue_music.py`:

```python
MIN_QUEUE_DEPTH = 10      # Minimum tracks before filling
TARGET_QUEUE_DEPTH = 20   # Fill to this level
RECENT_HISTORY_SIZE = 50  # Anti-repetition window
```

### Energy Flow Patterns

Edit pattern in `enqueue_music.py`:

```python
# Available patterns: "wave", "ascending", "descending", "mixed"
energy_flow = build_energy_flow(tracks_needed, pattern="wave")
```

## Test Results

All integration tests passing:
- ✅ Liquidsoap client module available
- ✅ Track selection module available
- ✅ Enqueue script executable
- ✅ Break scheduler executable
- ✅ Systemd unit files present
- ✅ Unit tests passing (6/6)

Run tests:
```bash
./scripts/test-phase5.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SCHEDULING & ORCHESTRATION                  │
├─────────────────────────────────────────────────────────────┤
│ Enqueue Service (every 5 min)                               │
│   1. Check music queue depth via socket                     │
│   2. If < MIN_QUEUE_DEPTH:                                  │
│      a. Build energy flow pattern                           │
│      b. Select tracks (avoid recent plays)                  │
│      c. Push to Liquidsoap queue                            │
├─────────────────────────────────────────────────────────────┤
│ Break Scheduler (every 5 min)                               │
│   1. Check if within 5 min of top of hour                   │
│   2. If yes:                                                 │
│      a. Check if break already queued (idempotency)         │
│      b. Find next.mp3 (or last_good.mp3 fallback)           │
│      c. Push to breaks queue                                │
├─────────────────────────────────────────────────────────────┤
│ Liquidsoap Consumes:                                         │
│   - Music queue (continuous playback)                       │
│   - Breaks queue (top of hour, force break triggers)        │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### src/ai_radio/liquidsoap_client.py:1
Unix socket communication client for Liquidsoap telnet interface.

**Methods:**
- `send_command(command)` - Send telnet command, return response
- `get_queue_length(queue_name)` - Get number of tracks in queue
- `push_track(queue_name, file_path)` - Push track to queue

**Error Handling:**
- Returns -1 for queue length on connection errors
- Returns False for push failures

### src/ai_radio/track_selection.py:1
Energy-aware track selection with anti-repetition.

**Functions:**
- `select_next_tracks()` - Select N tracks from database with energy preference
- `build_energy_flow()` - Generate energy pattern sequence

**Energy Levels:**
- High: energy_level >= 7
- Medium: 4 <= energy_level <= 6
- Low: energy_level <= 3

**Flow Patterns:**
- wave: medium → high → medium → low (cycling)
- ascending: low → medium → high → high
- descending: high → high → medium → low
- mixed: random energy levels

### scripts/enqueue_music.py:1
Music queue management service.

**Logic:**
1. Check current queue depth via Liquidsoap client
2. If < MIN_QUEUE_DEPTH, calculate tracks_needed
3. Build energy flow pattern
4. Select tracks matching energy pattern
5. Push tracks to music queue
6. Log results

### scripts/schedule_break.py:1
Break scheduling service.

**Logic:**
1. Check if within 5 minutes of top of hour (minutes 0-4)
2. Check if break already queued (idempotency)
3. Find next.mp3 in breaks directory
4. Fallback to last_good.mp3 if next.mp3 missing
5. Push break to breaks queue
6. Log result

**Critical Fix:** Changed `if minutes > 5` to `if minutes >= 5` to prevent double-scheduling at minute 5 (PAL Issue #2).

### systemd/ai-radio-break-scheduler.timer:9
Break scheduler timer using wall-clock alignment.

**Configuration:**
```ini
OnCalendar=*:0/5  # CRITICAL: Ensures deterministic timing
```

This fixes PAL Issue #1 where `OnUnitActiveSec` would drift and never land in the 0-5 minute window.

## Next Steps

Phase 6 will implement observability and monitoring:
- Play history tracking (write to SQLite play_history table)
- Queue metrics collection
- Health check endpoints
- Prometheus/Grafana integration
- Alert rules for failures

## SOW Compliance

✅ **Section 11:** Multi-level fallback chain (music + breaks)
✅ **Section 11:** Break insertion at top of hour
✅ **Section 13:** Energy-aware track selection
✅ **Section 13:** Anti-repetition logic
✅ **Section 9:** next.mp3 / last_good.mp3 rotation
✅ **Section 3:** Producer/consumer separation

## Verification Commands

```bash
# 1. Run integration tests
./scripts/test-phase5.sh

# 2. Run unit tests
uv run pytest tests/test_liquidsoap_client.py tests/test_track_selection.py -v

# 3. Test module imports
uv run python -c "from ai_radio.liquidsoap_client import LiquidsoapClient"
uv run python -c "from ai_radio.track_selection import select_next_tracks, build_energy_flow"

# 4. Verify systemd files (deployment)
ls systemd/ai-radio-*.{service,timer}
```

All commands should complete successfully without errors.

## Notes

- **Recent Play Tracking:** Phase 5 reads from play_history table. Phase 6 will implement writing to it.
- **Energy Flow:** "Wave" pattern provides balanced energy throughout broadcast day
- **Anti-Repetition:** Current implementation excludes last 50 played tracks
- **Break Timing:** 5-minute window at top of hour ensures breaks play near scheduled time
- **Break Idempotency:** Service checks if break already queued to prevent double-scheduling
- **Queue Depth:** 10-20 track range provides buffer without excessive lookahead
- **Resource Isolation:** CPU nice level 10 prevents starving Liquidsoap during intensive queries
- **Wall-Clock Alignment:** Break scheduler timer uses OnCalendar for deterministic timing
