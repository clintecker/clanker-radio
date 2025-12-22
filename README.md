# LAST BYTE RADIO - AI-Powered Cyberpunk Radio Station

An autonomous internet radio station that generates and broadcasts AI-created content with real music. Set in a post-capitalist dystopian cyber future, broadcasting from the neon-lit wasteland of Chicago.

> **Broadcasting from the ruins. Still here. Still transmitting. 📻**

## Features

- **Autonomous Broadcasting**: 24/7 automated radio station with minimal human intervention
- **AI-Generated Content**: News bulletins and weather reports with dystopian cyberpunk personality
- **Smart Scheduling**: Automatic station ID placement at :15/:30/:45, top-of-hour news breaks
- **Music Library Management**: SQLite-backed music database with play tracking and smart rotation
- **Professional Audio**: Liquidsoap streaming with crossfades, normalization, and background beds
- **Icecast Streaming**: Compatible with any Icecast2-compatible streaming server
- **Play History & Analytics**: Full tracking with a beautiful TUI for browsing
- **Safety Fallbacks**: Multiple fallback layers ensure the station never goes silent
- **Web Interface**: Cyber-terminal themed player with real-time now playing info

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LAST BYTE RADIO                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  AI Generation   │    │   Liquidsoap     │    │    Icecast       │
│                  │    │                  │    │                  │
│  Claude API  ────┼───▶│  Queue Mgmt  ────┼───▶│  MP3 Stream      │
│  Weather API     │    │  Crossfading     │    │  /radio          │
│  Voice Synth     │    │  Normalization   │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                       │                        │
        │                       │                        │
        ▼                       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   systemd        │    │   Unix Socket    │    │   Nginx          │
│                  │    │                  │    │                  │
│  Timers      ────┼───▶│  /run/liquidsoap │    │  Frontend        │
│  Services        │    │  radio.sock      │    │  API Endpoints   │
│  Orchestration   │    │                  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                       │                        │
        │                       │                        │
        ▼                       ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SQLite Database                             │
│  Assets | Play History | Metadata | Scheduler State             │
└─────────────────────────────────────────────────────────────────┘
```

## Requirements

### System Dependencies

- **Python 3.11+** - Core programming language
- **Liquidsoap 2.0+** - Audio streaming engine
- **Icecast2** - Streaming server
- **SQLite 3** - Database
- **FFmpeg** - Audio processing and normalization
- **Nginx** (optional) - Reverse proxy for web interface
- **Systemd** - Service management
- **uv** - Python package manager (recommended)
- **Go 1.23+** (optional) - For the TUI database browser

### Python Dependencies

Automatically installed via `uv sync`:
- `anthropic` - Claude AI for script generation
- `openai` (optional) - OpenAI TTS fallback or Gemini alternative
- `feedparser` - RSS news feed parsing
- `mutagen` - Audio file metadata
- `ffmpeg-normalize` - Audio normalization
- `pydantic` & `pydantic-settings` - Configuration management
- `httpx` - HTTP client for API calls
- `fasteners` - File locking for concurrency safety

See `pyproject.toml` for complete dependency list.

## Installation

### 1. System Setup

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3.11 liquidsoap icecast2 sqlite3 ffmpeg nginx

# Create radio user and directory
sudo useradd -r -s /bin/bash -d /srv/ai_radio ai-radio
sudo mkdir -p /srv/ai_radio
sudo chown ai-radio:ai-radio /srv/ai_radio
```

### 2. Clone Repository

```bash
cd /srv/ai_radio
sudo -u ai-radio git clone https://github.com/YOUR_USERNAME/clanker-radio.git .
```

### 3. Python Environment Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
sudo -u ai-radio uv venv
sudo -u ai-radio uv sync
```

### 4. Configure Environment Variables

Create `/srv/ai_radio/.env`:

```bash
# ============================================================================
# BASE CONFIGURATION
# ============================================================================
RADIO_BASE_PATH=/srv/ai_radio
RADIO_STATION_TZ=America/Chicago

# ============================================================================
# STATION IDENTITY
# ============================================================================
RADIO_STATION_NAME="LAST BYTE RADIO"
RADIO_STATION_LOCATION="Chicago"

# ============================================================================
# LOCATION FOR WEATHER (REQUIRED)
# ============================================================================
# Find coordinates at https://www.latlong.net/
RADIO_STATION_LAT=41.8781
RADIO_STATION_LON=-87.6298

# ============================================================================
# API KEYS (REQUIRED FOR PRODUCTION)
# ============================================================================

# Anthropic Claude - For news/weather script generation
# Get key at: https://console.anthropic.com/
RADIO_LLM_API_KEY=sk-ant-api03-your-key-here

# Claude model selection
RADIO_LLM_MODEL=claude-3-5-sonnet-latest

# ============================================================================
# TEXT-TO-SPEECH CONFIGURATION
# ============================================================================

# TTS Provider: "gemini" (recommended) or "openai"
RADIO_TTS_PROVIDER=gemini

# Option 1: Google Gemini TTS (RECOMMENDED - more natural voices)
# Get key at: https://aistudio.google.com/apikey
RADIO_GEMINI_API_KEY=your-gemini-api-key-here
RADIO_GEMINI_TTS_MODEL=gemini-2.5-pro-preview-tts
# Voice options: Kore, Puck, Charon, Aoede, Fenrir
RADIO_GEMINI_TTS_VOICE=Kore

# Option 2: OpenAI TTS (fallback)
# Get key at: https://platform.openai.com/api-keys
# RADIO_TTS_API_KEY=sk-your-openai-key-here
# RADIO_TTS_VOICE=alloy  # Options: alloy, echo, fable, onyx, nova, shimmer

# ============================================================================
# NATIONAL WEATHER SERVICE CONFIGURATION
# ============================================================================
# Find your grid at: https://www.weather.gov/ → enter location → click map → check URL
RADIO_NWS_OFFICE=LOT  # Chicago office
RADIO_NWS_GRID_X=76
RADIO_NWS_GRID_Y=73

# ============================================================================
# NEWS RSS FEEDS (Optional - customize your news sources)
# ============================================================================
# Default feeds are configured in config.py
# Override with JSON if needed:
# RADIO_NEWS_RSS_FEEDS='{"local": ["https://your-local-news.com/feed"], "tech": [...]}'

# ============================================================================
# CONTENT GENERATION SETTINGS (Optional)
# ============================================================================
RADIO_WEATHER_SCRIPT_TEMPERATURE=0.8  # 0.0=deterministic, 1.0=creative
RADIO_NEWS_SCRIPT_TEMPERATURE=0.6

# Hallucinated news (cyberpunk flavor)
RADIO_HALLUCINATE_NEWS=true
RADIO_HALLUCINATION_CHANCE=1.0  # 0.0-1.0 probability

# ============================================================================
# AUDIO SETTINGS (Optional - defaults are good)
# ============================================================================
RADIO_BED_VOLUME_DB=-18.0
RADIO_BED_PREROLL_SECONDS=3.0
RADIO_BED_FADEIN_SECONDS=2.0
RADIO_BED_POSTROLL_SECONDS=5.4
RADIO_BED_FADEOUT_SECONDS=3.0

# ============================================================================
# ANNOUNCER PERSONALITY (Optional - advanced customization)
# ============================================================================
RADIO_ENERGY_LEVEL=8  # 1-10, cap at 8-9 for radio
RADIO_VIBE_KEYWORDS="witty, darkly humorous, fast, slightly unhinged, defiant, cyberpunk survivor"
RADIO_MAX_RIFFS_PER_BREAK=1
RADIO_UNHINGED_PERCENTAGE=20
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete configuration documentation.

**Finding Your NWS Grid Coordinates:**
1. Go to https://www.weather.gov/
2. Enter your location
3. Click on your location on the map
4. The URL will contain your grid coordinates (e.g., `/gridpoint/LOT/76,73`)

### 5. Configure Icecast

Edit `/etc/icecast2/icecast.xml`:

```xml
<source-password>YOUR_SECURE_PASSWORD</source-password>
<hostname>radio.yourdomain.com</hostname>
```

Store the password in `/srv/ai_radio/.icecast_secrets`:

```bash
echo "YOUR_SECURE_PASSWORD" | sudo -u ai-radio tee /srv/ai_radio/.icecast_secrets
sudo chmod 600 /srv/ai_radio/.icecast_secrets
```

Enable and start Icecast:

```bash
sudo systemctl enable --now icecast2
```

### 6. Create Directory Structure

```bash
sudo -u ai-radio mkdir -p /srv/ai_radio/{assets/{music,beds,breaks,safety,bumpers},db,logs,tmp,state,public}
sudo -u ai-radio mkdir -p /srv/ai_radio/assets/breaks/archive
```

### 7. Initialize Database

```bash
# Run migrations in order
cd /srv/ai_radio
for migration in db/migrations/*.sql; do
    sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 < "$migration"
    echo "Applied: $migration"
done
```

### 8. Add Content

#### Music

See [ADDING_MUSIC.md](docs/ADDING_MUSIC.md) for detailed instructions.

```bash
# Quick start: batch ingest music
sudo -u ai-radio ./scripts/batch_ingest.sh /path/to/your/music/folder
```

#### Station IDs (Bumpers)

Place station ID files in `/srv/ai_radio/assets/bumpers/` with naming pattern `station_id_*.mp3` or `station_id_*.wav`. These play at :15, :30, and :45 past each hour.

#### Background Beds

Place instrumental music beds in `/srv/ai_radio/assets/beds/`. These provide background music for news breaks and fill gaps between content.

#### Safety Content

Place fallback audio in `/srv/ai_radio/assets/safety/evergreen.m3u` (playlist format). This plays if all other content sources fail.

#### Startup Jingle

Place an 18-second startup jingle at `/srv/ai_radio/assets/startup.mp3`. This plays once when Liquidsoap starts, giving time for the music queue to fill.

### 9. Install Systemd Services

```bash
# Copy service and timer files
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable --now ai-radio-liquidsoap
sudo systemctl enable --now ai-radio-enqueue.timer
sudo systemctl enable --now ai-radio-schedule-station-id.timer
sudo systemctl enable --now ai-radio-break-scheduler.timer
sudo systemctl enable --now ai-radio-export-nowplaying.timer
```

### 10. Configure Liquidsoap Socket Permissions

```bash
# Create liquidsoap socket directory
sudo mkdir -p /run/liquidsoap
sudo chown ai-radio:ai-radio /run/liquidsoap
sudo chmod 770 /run/liquidsoap

# Add your user to ai-radio group (for management scripts)
sudo usermod -a -G ai-radio $USER
```

### 11. Configure Nginx (Optional Web Interface)

```bash
# Copy nginx configurations
sudo cp nginx/radio.conf /etc/nginx/sites-available/
sudo cp nginx/now_playing.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/radio.conf /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/now_playing.conf /etc/nginx/sites-enabled/

# Copy frontend files
sudo -u ai-radio cp -r nginx/admin/ /srv/ai_radio/public/
sudo -u ai-radio cp nginx/index.html /srv/ai_radio/public/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

## Configuration

### API Keys Required

| Service | Environment Variable | Purpose | Where to Get | Notes |
|---------|---------------------|---------|--------------|-------|
| Anthropic Claude | `RADIO_LLM_API_KEY` | Script generation for news/weather | https://console.anthropic.com/ | **Required** |
| Google Gemini | `RADIO_GEMINI_API_KEY` | TTS voice synthesis | https://aistudio.google.com/apikey | Recommended for better voices |
| OpenAI | `RADIO_TTS_API_KEY` | TTS fallback | https://platform.openai.com/ | Optional alternative |

### Customization

See [CONFIGURATION.md](CONFIGURATION.md) for comprehensive customization documentation including:

- Station personality and voice characteristics (energy, vibe, humor style)
- News feed sources (local, national, politics, tech)
- Weather presentation style
- Audio processing parameters (crossfade, normalization, bed timing)
- Scheduling intervals (music rotation, breaks, station IDs)
- Hallucinated news settings (cyberpunk world-building)
- Announcer personality controls (chaos budget, humor guardrails)

### Station Scheduling

| Service | Timing | Purpose |
|---------|--------|---------|
| Music Enqueue | Every 2 minutes | Maintains 20-track buffer in queue |
| Station IDs | :15, :30, :45 | Scheduled at :14, :29, :44; plays at track boundary |
| Top-of-Hour Breaks | :00 | News + weather, scheduled at :59 |
| Now Playing Export | Every 10 seconds | Updates web interface |

Modify timing in the corresponding `systemd/*.timer` files.

## Usage

### Start the Station

```bash
# Start all services
sudo systemctl start ai-radio-liquidsoap
sudo systemctl start ai-radio-enqueue.timer
sudo systemctl start ai-radio-schedule-station-id.timer
sudo systemctl start ai-radio-break-scheduler.timer
sudo systemctl start ai-radio-export-nowplaying.timer
```

### Monitor Status

```bash
# Check service status
sudo systemctl status ai-radio-liquidsoap
sudo systemctl status ai-radio-enqueue.timer
sudo systemctl list-timers ai-radio-*

# View logs
sudo journalctl -u ai-radio-liquidsoap -f
sudo journalctl -u ai-radio-break-scheduler -f

# Check Liquidsoap logs
sudo tail -f /srv/ai_radio/logs/liquidsoap.log
```

### Stream URL

Access your stream at:
```
http://your-server:8000/radio
```

M3U playlist:
```
http://your-server/stream.m3u
```

### Browse Database (TUI)

A beautiful terminal UI for browsing your music library and play history:

```bash
# Install Go TUI dependencies
go mod download

# Sync database from production to local machine
./scripts/sync_db.sh

# Launch TUI
go run ./cmd/radiotui
# Or use make
make tui
```

**TUI Controls:**
- `1` - Track list view (sortable by artist, title, album, duration, energy, plays, last played)
- `2` - Track detail view (full metadata including LUFS, dBTP, energy)
- `3` - Station stats (total tracks, plays, uptime)
- `4` - Play history (time, source, track)
- `Tab` - Cycle sort columns
- `Shift+Tab` - Reverse sort direction
- `↑/↓` - Navigate lists
- `Enter` - View details (in track list)
- `Esc` - Go back
- `q` - Quit

### Manual Queue Management

```bash
# Queue music tracks (automatic via timer, but can run manually)
sudo -u ai-radio .venv/bin/python scripts/enqueue_music.py

# Queue a station ID immediately (bypasses schedule)
sudo -u ai-radio .venv/bin/python scripts/enqueue_station_id.py

# Generate and queue a break now (bypasses top-of-hour schedule)
sudo -u ai-radio .venv/bin/python scripts/schedule_break.py

# Check queue contents via Liquidsoap
echo "music.queue" | nc -U /run/liquidsoap/radio.sock
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock

# Skip current track
echo "music.skip" | nc -U /run/liquidsoap/radio.sock
```

## Directory Structure

```
/srv/ai_radio/
├── assets/
│   ├── music/           # Music library (ingested, content-addressable)
│   ├── beds/            # Instrumental background beds
│   ├── breaks/          # Generated news/weather breaks
│   │   └── archive/     # Old breaks (auto-archived after 50 min)
│   ├── safety/          # Emergency fallback audio
│   │   └── evergreen.m3u  # Safety playlist
│   ├── bumpers/         # Station ID files (station_id_*.mp3)
│   └── startup.mp3      # Startup jingle (18 seconds)
├── config/
│   └── radio.liq        # Liquidsoap configuration
├── db/
│   ├── radio.sqlite3    # Main database
│   └── migrations/      # Database schema migrations
│       ├── 001_initial_schema.sql
│       ├── 002_add_track_metadata.sql
│       ├── 003_add_play_history.sql
│       └── 004_add_scheduler_state.sql
├── logs/
│   ├── liquidsoap.log   # Streaming engine logs
│   └── jobs.jsonl       # Python service logs
├── public/              # Web frontend (if using nginx)
│   ├── index.html       # Cyber-terminal player
│   ├── admin/           # Admin interface
│   └── now_playing.json # Real-time metadata
├── scripts/             # Management and automation scripts
│   ├── batch_ingest.sh
│   ├── enqueue_music.py
│   ├── schedule_break.py
│   ├── schedule_station_id.py
│   ├── record_play.py
│   ├── export_now_playing.py
│   └── sync_db.sh
├── src/ai_radio/        # Python application code
│   ├── audio_mixer.py
│   ├── break_generator.py
│   ├── config.py
│   ├── liquidsoap_client.py
│   ├── news.py
│   ├── play_history.py
│   ├── script_writer.py
│   ├── voice_synth.py
│   └── weather.py
├── systemd/             # Service definitions
│   ├── ai-radio-liquidsoap.service
│   ├── ai-radio-enqueue.{service,timer}
│   ├── ai-radio-schedule-station-id.{service,timer}
│   ├── ai-radio-break-scheduler.{service,timer}
│   └── ai-radio-export-nowplaying.{service,timer}
├── tmp/                 # Temporary working files
├── state/               # Application state
├── .env                 # Environment configuration (CREATE THIS)
└── .icecast_secrets     # Icecast password (CREATE THIS)
```

## Troubleshooting

### No Audio Playing

1. Check Liquidsoap status:
   ```bash
   sudo systemctl status ai-radio-liquidsoap
   sudo journalctl -u ai-radio-liquidsoap -n 50
   ```

2. Verify music is ingested:
   ```bash
   ls -lh /srv/ai_radio/assets/music/
   sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE kind='music';"
   ```

3. Check enqueue service:
   ```bash
   sudo systemctl status ai-radio-enqueue.timer
   sudo systemctl start ai-radio-enqueue.service
   ```

4. Check Liquidsoap queue:
   ```bash
   echo "music.queue" | nc -U /run/liquidsoap/radio.sock
   ```

### Station IDs Interrupting Music Mid-Track

**This has been fixed** by removing the buffer from `break_queue`. If you still experience interruptions:

1. Verify config shows no buffer:
   ```bash
   grep "break_queue = " /srv/ai_radio/config/radio.liq
   # Should show: break_queue = request.queue(id="breaks")
   # NOT: break_queue = buffer(request.queue(id="breaks"))
   ```

2. Restart Liquidsoap:
   ```bash
   sudo systemctl restart ai-radio-liquidsoap
   ```

3. Check `track_sensitive=true` is set:
   ```bash
   grep "track_sensitive" /srv/ai_radio/config/radio.liq
   ```

The `track_sensitive=true` parameter ensures breaks wait for the current track to finish before playing.

### Breaks Not Playing or Scheduling

1. Check break scheduler:
   ```bash
   sudo systemctl status ai-radio-break-scheduler.timer
   sudo journalctl -u ai-radio-break-scheduler -n 20
   ```

2. Verify breaks are generated:
   ```bash
   ls -lh /srv/ai_radio/assets/breaks/
   ```

3. Check API keys:
   ```bash
   grep RADIO_LLM_API_KEY /srv/ai_radio/.env
   grep RADIO_GEMINI_API_KEY /srv/ai_radio/.env
   ```

4. Manually trigger a break:
   ```bash
   sudo -u ai-radio .venv/bin/python scripts/schedule_break.py
   ```

5. Check breaks queue:
   ```bash
   echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock
   ```

### API Rate Limits or Errors

1. Check for rate limit errors:
   ```bash
   sudo journalctl -u ai-radio-break-scheduler | grep -i "rate\|error\|failed"
   ```

2. Verify API keys are valid:
   - Claude: https://console.anthropic.com/
   - Gemini: https://aistudio.google.com/

3. Reduce break generation frequency (edit timer OnCalendar):
   ```bash
   sudo systemctl edit ai-radio-break-scheduler.timer
   ```

### Database Locked Errors

SQLite locks when multiple processes access simultaneously:

1. Check for competing processes:
   ```bash
   sudo lsof /srv/ai_radio/db/radio.sqlite3
   ```

2. Verify scripts close connections properly

3. Increase timeout in Python scripts:
   ```python
   conn = sqlite3.connect(config.db_path, timeout=10.0)
   ```

### Permission Issues

```bash
# Fix ownership
sudo chown -R ai-radio:ai-radio /srv/ai_radio

# Fix socket permissions
sudo chown ai-radio:ai-radio /run/liquidsoap/radio.sock
sudo chmod 660 /run/liquidsoap/radio.sock

# Verify your user is in ai-radio group
groups | grep ai-radio
```

### Frontend Not Updating

1. Check export timer:
   ```bash
   sudo systemctl status ai-radio-export-nowplaying.timer
   sudo systemctl list-timers ai-radio-export-nowplaying.timer
   ```

2. Verify JSON file exists and updates:
   ```bash
   ls -lh /srv/ai_radio/public/now_playing.json
   watch -n 1 'cat /srv/ai_radio/public/now_playing.json'
   ```

3. Check nginx serving:
   ```bash
   curl http://localhost/now_playing.json
   ```

## Development

### Running Tests

```bash
uv run pytest tests/ -v --cov=src/ai_radio
```

### Code Quality

```bash
# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Local Development

```bash
# Install dependencies
uv sync

# Run a script locally
uv run python scripts/enqueue_music.py

# Test Liquidsoap config syntax
liquidsoap --check config/radio.liq
```

## Database Schema

### Assets Table
```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,              -- SHA256 hash (content-addressable)
    path TEXT UNIQUE NOT NULL,        -- File path
    kind TEXT NOT NULL,               -- music/break/bed/bumper/safety
    duration_sec REAL NOT NULL,       -- Duration in seconds
    loudness_lufs REAL,               -- Integrated loudness (EBU R128)
    true_peak_dbtp REAL,              -- True peak level
    energy_level INTEGER,             -- 0-100 scale (for music selection)
    title TEXT,                       -- Track title
    artist TEXT,                      -- Artist name
    album TEXT,                       -- Album name
    created_at TEXT NOT NULL          -- ISO 8601 timestamp
);
```

### Play History Table
```sql
CREATE TABLE play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,           -- References assets(id)
    played_at TEXT NOT NULL,          -- ISO 8601 timestamp
    source TEXT NOT NULL,             -- music/break/bumper/bed
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);
```

### Scheduler State Table
```sql
CREATE TABLE scheduler_state (
    key TEXT PRIMARY KEY,             -- State key (e.g., "station_id_scheduled")
    value TEXT NOT NULL,              -- State value (e.g., "22:45")
    updated_at TEXT NOT NULL          -- ISO 8601 timestamp
);
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Follow existing code style
5. Ensure all tests pass
6. Test on a development server
7. Submit a pull request

## License

[Your chosen license - e.g., MIT, GPL, etc.]

## Credits

Built with:
- [Liquidsoap](https://www.liquidsoap.info/) - Audio streaming engine
- [Anthropic Claude](https://www.anthropic.com/) - AI script generation
- [Google Gemini](https://ai.google.dev/) - TTS voice synthesis
- [Icecast](https://icecast.org/) - Streaming server
- [Python](https://www.python.org/) - Application logic
- [Bubbletea](https://github.com/charmbracelet/bubbletea) - Beautiful TUI framework

## Support

For issues, questions, or contributions:
- GitHub Issues: [Your repo URL]
- Documentation: See `docs/` directory

---

**Broadcasting from the neon-lit wasteland. Still here. Still transmitting. 📻**
