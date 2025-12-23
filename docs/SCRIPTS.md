# Scripts Reference

Complete reference for all scripts in the AI Radio Station project. Scripts are organized by purpose.

---

## Quick Reference

| Script | Purpose | Runs Via |
|--------|---------|----------|
| `enqueue_music.py` | Fill music queue | systemd timer (every 2 min) |
| `schedule_break.py` | Queue top-of-hour break | systemd timer (every 5 min, runs at :00) |
| `schedule_station_id.py` | Queue station ID | systemd timer (:14, :29, :44) |
| `record_play.py` | Log play history | Liquidsoap callback |
| `export_now_playing.py` | Update web interface | systemd timer (every 10 sec) |
| `deploy.sh` | Deploy to production | Manual |
| `health_check.py` | Check service status | Manual or cron |
| `batch_ingest.sh` | Ingest music library | Manual |
| `sync_db.sh` | Sync database locally | Manual |

---

## Core Operations

Scripts that keep the station running, typically automated via systemd timers.

### enqueue_music.py

**Purpose:** Maintains the music queue at target depth by selecting and pushing tracks to Liquidsoap.

**Runs:** Automatically via `ai-radio-enqueue.timer` (every 2 minutes)

**What it does:**
- Checks current music queue depth
- If below minimum (3 tracks), fills to target (8 tracks)
- Selects tracks using smart energy flow algorithm
- Avoids recently played tracks (last 20)
- Pushes selected tracks to Liquidsoap via Unix socket

**Manual usage:**
```bash
# Run from project root
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_music.py
```

**Configuration:**
- `MIN_QUEUE_DEPTH` - Triggers refill (default: 3)
- `TARGET_QUEUE_DEPTH` - Fill to this level (default: 8)
- `RECENT_HISTORY_SIZE` - Avoid last N tracks (default: 20)

**Related:** `diagnose_track_selection.py` for debugging track selection

---

### schedule_break.py

**Purpose:** Pushes top-of-hour breaks (news + weather) to the breaks queue.

**Runs:** Automatically via `ai-radio-break-scheduler.timer` (every 5 min, queues at top of hour)

**What it does:**
- Checks if we're within 5 minutes of the hour
- Prevents double-scheduling by checking queue
- Finds most recent `break_*.mp3` file
- Pushes break to Liquidsoap breaks queue
- Archives old breaks (moves to `breaks/archive/`)

**Manual usage:**
```bash
# Queue a break immediately (bypasses schedule)
cd /srv/ai_radio
.venv/bin/python scripts/schedule_break.py
```

**How breaks are created:**
1. `generate_break.py` creates the break audio
2. `schedule_break.py` queues it for playback
3. Old breaks auto-archive after being played

**Related:** `generate_break.py`, `update_next_break.py`

---

### schedule_station_id.py

**Purpose:** Queues station ID bumpers at :15, :30, and :45 past the hour.

**Runs:** Automatically via `ai-radio-schedule-station-id.timer` (at :14, :29, :44)

**What it does:**
- Checks if we're near a station ID time (:15, :30, :45)
- Prevents double-scheduling by checking queue
- Picks a random station ID from `assets/bumpers/`
- Pushes to breaks queue (same queue as news breaks)
- Updates scheduler state to prevent duplicate scheduling

**Manual usage:**
```bash
# Queue a station ID immediately (bypasses schedule)
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_station_id.py
```

**Requirements:**
- Station ID files in `/srv/ai_radio/assets/bumpers/`
- Naming pattern: `station_id_*.mp3` or `station_id_*.wav`
- Files should be 5-15 seconds long

**Note:** Station IDs use the breaks queue but are detected as "bumper" source type in play history and web interface.

---

### record_play.py

**Purpose:** Records play history to database when tracks finish playing.

**Runs:** Automatically via Liquidsoap `on_track` callback

**What it does:**
- Receives track path from Liquidsoap
- Looks up asset in database by path
- Records play event with timestamp and source type
- Updates play history table for analytics

**Not run manually** - Liquidsoap calls this automatically.

**Configuration in `config/radio.liq`:**
```liquidsoap
music_queue.on_track(fun(m) ->
  system("/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/record_play.py " ^
         quote(m["filename"]) ^ " music")
end)
```

**Database:** Writes to `play_history` table with:
- `asset_id` - Track identifier (SHA256)
- `played_at` - ISO 8601 timestamp with timezone
- `source` - music/break/bumper/bed
- `hour_bucket` - For hourly analytics

---

### export_now_playing.py

**Purpose:** Exports current playback metadata to JSON for web interface.

**Runs:** Automatically via `ai-radio-export-nowplaying.timer` (every 10 seconds)

**What it does:**
- Queries Liquidsoap for current track metadata
- Queries database for play history (last 10 tracks)
- Detects source type (music/break/bumper/bed) from path
- Generates `now_playing.json` with:
  - Current track (title, artist, album, source)
  - Recent history
  - Station info
- Writes to `/srv/ai_radio/public/now_playing.json`

**Manual usage:**
```bash
# Update now playing JSON immediately
cd /srv/ai_radio
.venv/bin/python scripts/export_now_playing.py
```

**Output format:**
```json
{
  "current": {
    "title": "Track Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "source": "music",
    "started_at": "2025-12-23T12:34:56Z"
  },
  "history": [...],
  "station": {
    "name": "Your Station Name",
    "location": "Your City"
  }
}
```

**Frontend:** Web player polls this file every 10 seconds for updates.

---

## Deployment & Administration

Scripts for deploying code and managing the production server.

### deploy.sh

**Purpose:** Automated deployment to production server with permission handling.

**Runs:** Manually when deploying changes

**Usage:**
```bash
# Deploy everything (frontend + scripts + code)
./scripts/deploy.sh

# Deploy specific components
./scripts/deploy.sh frontend    # HTML/CSS/JS only
./scripts/deploy.sh scripts     # Python scripts only
./scripts/deploy.sh code        # src/ai_radio package
./scripts/deploy.sh config      # Liquidsoap config (prompts for restart)
./scripts/deploy.sh systemd     # Service/timer files (requires sudo)

# Check service health after deployment
./scripts/deploy.sh health
```

**What it deploys:**
- `frontend` - `nginx/index.html`, `nginx/stream.m3u` → `/srv/ai_radio/public/`
- `scripts` - All `scripts/*.py` → `/srv/ai_radio/scripts/` (sets +x)
- `code` - `src/ai_radio/` → `/srv/ai_radio/src/ai_radio/`
- `config` - `config/radio.liq` → `/srv/ai_radio/config/` (prompts for restart)
- `systemd` - `systemd/*.{service,timer}` → `/etc/systemd/system/` (runs daemon-reload)

**Features:**
- ✅ Automatic permission fixing (chown/chmod)
- ✅ Safe staging through home directory
- ✅ Color-coded output (green=success, red=error, yellow=warning)
- ✅ Error handling with rollback
- ✅ Health checks after deployment

**Configuration:**
Create `.deploy_config` with:
```bash
DEPLOY_SERVER=user@hostname
DEPLOY_BASE_PATH=/srv/ai_radio
DEPLOY_USER=ai-radio
```

**After deployment:** Script automatically shows service health. Failed oneshot services (like `ai-radio-export-nowplaying.service`) are normal - timers trigger them periodically.

---

### health_check.py

**Purpose:** Comprehensive service health check with detailed diagnostics.

**Runs:** Manually or via cron/monitoring system

**Usage:**
```bash
# Run health check
cd /srv/ai_radio
.venv/bin/python scripts/health_check.py

# Quick check (returns exit code only)
./scripts/deploy.sh health
```

**Checks:**
- ✅ Liquidsoap service status
- ✅ All timer services enabled and active
- ✅ Queue depths (music and breaks)
- ✅ Music library size (minimum 20 tracks)
- ✅ Recent play activity (played within last 10 minutes)
- ✅ Now playing JSON exists and is recent
- ✅ Service log errors (last 20 entries)

**Output format:**
```
✓ ai-radio-liquidsoap.service (active/running)
✓ ai-radio-enqueue.timer (active/waiting)
⚠ ai-radio-export-nowplaying.service (failed) - Normal for oneshot
✗ Music queue depth: 0 (minimum: 3)
```

**Exit codes:**
- `0` - All healthy
- `1` - Warnings (some issues detected)
- `2` - Critical failures

**Use in monitoring:** Add to cron or Nagios/Prometheus for automated monitoring.

---

## Utilities & Tools

Scripts for managing music, databases, and day-to-day operations.

### batch_ingest.sh

**Purpose:** Batch ingest music files from a directory into the radio database.

**Runs:** Manually when adding music

**Usage:**
```bash
# Ingest all music from a folder
./scripts/batch_ingest.sh /path/to/music/folder

# Ingest and normalize audio levels
./scripts/batch_ingest.sh --normalize /path/to/music/folder
```

**What it does:**
1. Recursively finds all audio files (mp3, flac, ogg, opus, m4a, wav)
2. For each file:
   - Computes SHA256 hash (content-addressable)
   - Analyzes audio (duration, loudness, true peak)
   - Extracts metadata (title, artist, album)
   - Computes energy level (0-100 scale)
   - Copies to `/srv/ai_radio/assets/music/` as `{hash}.{ext}`
   - Inserts record into database
3. Skips already-ingested files (hash match)
4. Reports progress and statistics

**Requirements:**
- FFmpeg installed (for analysis)
- SQLite3 installed (for database)
- Python virtual environment activated

**Performance:** Processes ~1 file per second. 1000 tracks ≈ 15-20 minutes.

**See also:** [Adding Music documentation](ADDING_MUSIC.md)

---

### sync_db.sh

**Purpose:** Sync production database to local machine for development/analysis.

**Runs:** Manually when you want to browse the TUI locally

**Usage:**
```bash
# Sync database from production
./scripts/sync_db.sh

# Then run TUI
go run ./cmd/radiotui
```

**What it does:**
- Uses `rsync` to copy remote database
- Preserves timestamps and permissions
- Creates local `data/` directory if needed
- Displays transfer progress

**Configuration:**
Edit script to set `REMOTE_SERVER` and `REMOTE_DB_PATH`:
```bash
REMOTE_SERVER="user@hostname"
REMOTE_DB_PATH="/srv/ai_radio/db/radio.sqlite3"
```

**Use cases:**
- Browse play history locally
- Test track selection algorithms
- Analyze station statistics
- Debug without affecting production

---

### generate_break.py

**Purpose:** Generate a single news/weather break using AI.

**Runs:** Manually or via external scheduler

**Usage:**
```bash
# Generate one break now
cd /srv/ai_radio
.venv/bin/python scripts/generate_break.py
```

**What it does:**
1. Fetches news from configured RSS feeds
2. Fetches weather from National Weather Service
3. Generates hallucinated news (if enabled)
4. Calls Claude API to write script
5. Calls Gemini/OpenAI TTS to synthesize voice
6. Mixes voice with background bed
7. Saves as `break_{timestamp}.mp3` in `assets/breaks/`
8. Duration: typically 2-4 minutes

**Requirements:**
- `RADIO_LLM_API_KEY` (Claude)
- `RADIO_GEMINI_API_KEY` or `RADIO_TTS_API_KEY` (TTS)
- Background beds in `assets/beds/`
- FFmpeg installed

**Configuration:** All via `.env` file (news feeds, weather location, TTS voice, energy level, etc.)

**Related:** `schedule_break.py` to queue the generated break

---

### generate_startup_voice.py

**Purpose:** Generate the 18-second startup jingle that plays when Liquidsoap starts.

**Runs:** Manually (usually just once during setup)

**Usage:**
```bash
# Generate startup jingle
cd /srv/ai_radio
.venv/bin/python scripts/generate_startup_voice.py
```

**What it does:**
1. Generates greeting script ("You're listening to [station name]...")
2. Synthesizes voice using TTS
3. Mixes with background bed
4. Saves as `assets/startup.mp3`
5. Duration: exactly 18 seconds (padded to match Liquidsoap buffer time)

**Purpose of startup jingle:** Liquidsoap needs ~18 seconds to start up and fill the music queue. The startup jingle plays during this time to prevent silence.

**When to regenerate:**
- After changing station name
- After changing announcer voice
- After changing TTS provider

---

### update_next_break.py

**Purpose:** Update the next break time in systemd timer.

**Runs:** Manually (rarely needed)

**Usage:**
```bash
# Set next break to run at specific time
cd /srv/ai_radio
.venv/bin/python scripts/update_next_break.py --next-time "18:59"

# Reset to default hourly schedule
.venv/bin/python scripts/update_next_break.py --reset
```

**What it does:**
- Modifies systemd timer `OnCalendar` setting
- Runs `systemctl daemon-reload`
- Restarts timer to apply changes

**Use cases:**
- Skip a break (set next time to 1 hour later)
- Force an early break (set next time to now)
- Adjust schedule temporarily

**Warning:** Changes are temporary. Restarting the timer service resets to default schedule.

---

## Development & Debugging

Scripts for diagnosing issues and testing functionality.

### diagnose_track_selection.py

**Purpose:** Diagnose track selection algorithm and energy flow.

**Runs:** Manually when debugging track selection issues

**Usage:**
```bash
# Show diagnostic info for track selection
cd /srv/ai_radio
.venv/bin/python scripts/diagnose_track_selection.py
```

**What it shows:**
- Total tracks in database
- Energy level distribution histogram
- Recently played tracks (last 20)
- Sample of available tracks (not recently played)
- Energy flow computation details
- Simulated track selection

**Use cases:**
- Why are certain tracks never playing?
- Is energy flow working correctly?
- Are tracks being marked as recently played?
- Is the database populated correctly?

**Example output:**
```
Total tracks: 247
Energy distribution: [  *  ] 0-20: 12
                     [ *** ] 21-40: 45
                     [*****] 41-60: 98
                     [ *** ] 61-80: 67
                     [  *  ] 81-100: 25

Recently played (last 20): [48, 52, 61, ...]
Available tracks: 227
Selecting 8 tracks with energy flow: [40, 55, 62, 71, 65, 58, 48, 42]
```

---

### check_gemini_quota.py

**Purpose:** Check Google Gemini API quota and usage.

**Runs:** Manually when debugging TTS issues

**Usage:**
```bash
# Check Gemini quota
cd /srv/ai_radio
.venv/bin/python scripts/check_gemini_quota.py
```

**What it shows:**
- Current API key status
- Quota limits (requests per minute, per day)
- Current usage
- Remaining quota
- Estimated time until reset

**Use cases:**
- Break generation failing with rate limit errors
- TTS synthesis timing out
- Planning break generation schedule to stay under quota

---

### test-phase5.sh

**Purpose:** Integration test for Phase 5 features (music queuing, energy flow).

**Runs:** Manually during development

**Usage:**
```bash
# Run Phase 5 integration test
./scripts/test-phase5.sh
```

**What it tests:**
- Database connectivity
- Music ingestion
- Track selection algorithm
- Energy flow computation
- Queue management
- Liquidsoap communication

**Output:** Pass/fail status for each test phase.

**When to run:**
- After major code changes
- Before deploying to production
- When debugging queue issues

---

## One-Time Migration Scripts

Scripts that fix historical data or perform one-time operations. Generally not needed for new installations.

### fix_timestamp_formats.py

**Purpose:** Fix timestamp format inconsistency in play_history table (one-time migration).

**Status:** Completed on 2025-12-22. Not needed for new installations.

**What it fixed:**
- Converted old SQLite timestamps (`YYYY-MM-DD HH:MM:SS`) to ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`)
- Fixed 73 historical records with wrong format
- Ensures correct chronological sorting in play history

**Background:** Early versions of `record_play.py` used two different timestamp formats causing breaks/station IDs to appear out of order. This migration fixed the historical data.

**Run once if upgrading from pre-2025-12-22 version:**
```bash
cd /srv/ai_radio
.venv/bin/python scripts/fix_timestamp_formats.py
```

---

## Systemd Integration

Scripts are orchestrated via systemd services and timers. Here's how they connect:

### Services

| Service | Script | Type | Purpose |
|---------|--------|------|---------|
| `ai-radio-liquidsoap.service` | N/A (runs liquidsoap) | daemon | Audio streaming engine |
| `ai-radio-enqueue.service` | `enqueue_music.py` | oneshot | Fill music queue |
| `ai-radio-break-scheduler.service` | `schedule_break.py` | oneshot | Queue top-of-hour break |
| `ai-radio-schedule-station-id.service` | `schedule_station_id.py` | oneshot | Queue station ID |
| `ai-radio-export-nowplaying.service` | `export_now_playing.py` | oneshot | Update web interface |

### Timers

| Timer | Triggers | Schedule |
|-------|----------|----------|
| `ai-radio-enqueue.timer` | `ai-radio-enqueue.service` | Every 2 minutes |
| `ai-radio-break-scheduler.timer` | `ai-radio-break-scheduler.service` | Every 5 min (runs at :00) |
| `ai-radio-schedule-station-id.timer` | `ai-radio-schedule-station-id.service` | :14, :29, :44 |
| `ai-radio-export-nowplaying.timer` | `ai-radio-export-nowplaying.service` | Every 10 seconds |

**View timer status:**
```bash
systemctl list-timers ai-radio-*
```

**Failed oneshot services are normal** - they run, complete, and exit. The timer triggers them again at the next interval.

---

## Common Workflows

### Adding Music

1. Copy music to a staging directory
2. Run `batch_ingest.sh`:
   ```bash
   ./scripts/batch_ingest.sh /path/to/music
   ```
3. Wait for ingestion to complete
4. Verify tracks appear in database:
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE kind='music';"
   ```
5. Music will automatically start playing within 2 minutes (next enqueue cycle)

### Deploying Code Changes

1. Make changes locally and test
2. Commit changes to git
3. Deploy to production:
   ```bash
   # Frontend changes only (fast)
   ./scripts/deploy.sh frontend

   # Python code changes
   ./scripts/deploy.sh code

   # Everything
   ./scripts/deploy.sh
   ```
4. Check service health:
   ```bash
   ./scripts/deploy.sh health
   ```
5. If services need restart:
   ```bash
   ssh user@server 'sudo systemctl restart ai-radio-liquidsoap'
   ```

### Debugging Playback Issues

1. Check service status:
   ```bash
   ./scripts/deploy.sh health
   ```
2. Check queue depths:
   ```bash
   echo "music.queue" | nc -U /run/liquidsoap/radio.sock
   echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock
   ```
3. Check recent plays:
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT * FROM play_history ORDER BY played_at DESC LIMIT 10;"
   ```
4. Run track selection diagnostics:
   ```bash
   .venv/bin/python scripts/diagnose_track_selection.py
   ```
5. Check logs:
   ```bash
   journalctl -u ai-radio-liquidsoap -n 50
   journalctl -u ai-radio-enqueue -n 20
   ```

### Analyzing Station Performance

1. Sync database locally:
   ```bash
   ./scripts/sync_db.sh
   ```
2. Launch TUI:
   ```bash
   go run ./cmd/radiotui
   ```
3. Browse:
   - Press `1` - Track list (see play counts, last played)
   - Press `3` - Station stats (total plays, uptime)
   - Press `4` - Play history (chronological log)

### Generating and Scheduling a Break

**Option 1: Automatic (top of hour)**

Breaks generate and schedule automatically at the top of each hour.

**Option 2: Manual (immediate)**

```bash
# Generate break
cd /srv/ai_radio
.venv/bin/python scripts/generate_break.py

# Schedule it for playback
.venv/bin/python scripts/schedule_break.py
```

Break will play at the next track boundary.

---

## Environment Variables

All scripts use configuration from `.env` file via `src/ai_radio/config.py`. Key variables:

**Paths:**
- `RADIO_BASE_PATH` - Base directory (default: `/srv/ai_radio`)
- `RADIO_DB_PATH` - Database path (default: `$BASE_PATH/db/radio.sqlite3`)

**API Keys:**
- `RADIO_LLM_API_KEY` - Anthropic Claude (script generation)
- `RADIO_GEMINI_API_KEY` - Google Gemini (TTS)
- `RADIO_TTS_API_KEY` - OpenAI (TTS fallback)

**Liquidsoap:**
- `RADIO_LIQUIDSOAP_SOCKET` - Unix socket path (default: `/run/liquidsoap/radio.sock`)

See [Configuration Guide](CONFIGURATION.md) for complete variable reference.

---

## Troubleshooting Scripts

### Script won't run: Permission denied

```bash
# Make script executable
chmod +x scripts/script_name.py
```

### Script can't find modules: No module named 'ai_radio'

```bash
# Activate virtual environment first
cd /srv/ai_radio
source .venv/bin/activate
python scripts/script_name.py
```

### Script fails: Database locked

SQLite locks when multiple processes access simultaneously. Wait a moment and retry, or check for stuck processes:

```bash
# Find processes using database
sudo lsof /srv/ai_radio/db/radio.sqlite3
```

### Script fails: Can't connect to Liquidsoap socket

```bash
# Check if Liquidsoap is running
sudo systemctl status ai-radio-liquidsoap

# Check socket exists and has correct permissions
ls -l /run/liquidsoap/radio.sock
sudo chmod 660 /run/liquidsoap/radio.sock
sudo chown ai-radio:ai-radio /run/liquidsoap/radio.sock
```

### Timer not triggering: Service inactive

```bash
# Check timer status
systemctl status ai-radio-enqueue.timer

# Enable and start timer
sudo systemctl enable --now ai-radio-enqueue.timer

# Verify timer schedule
systemctl list-timers ai-radio-*
```

---

## See Also

- [Administration Guide](ADMINISTRATION.md) - Day-to-day operations *(coming soon)*
- [Configuration Guide](CONFIGURATION.md) - Environment variables
- [Deployment Guide](DEPLOYMENT.md) - Initial setup
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Issue diagnosis *(coming soon)*
- [Adding Music](ADDING_MUSIC.md) - Music library management
