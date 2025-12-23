# AI Radio Station - Autonomous Broadcasting Platform

An autonomous internet radio station that generates and broadcasts AI-created content with real music. Highly customizable with personality, world-building, and content generation settings.

**Out of the box:** A laid-back tropical island radio station (WKRP Coconut Island 🌴). **With configuration:** Cyberpunk dystopia, jazz cafe, college radio, pirate station - whatever you want!

> **Your autonomous radio station. Configure it your way. 📻**

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

## Getting Started

### Quick Start (3 Steps)

1. **[VM Setup](docs/VM_SETUP.md)** - Set up your Ubuntu server (30-45 min)
2. **[Configuration](docs/CONFIGURATION.md)** - Configure your station's personality (45-60 min)
3. **[Deployment](docs/DEPLOYMENT.md)** - Deploy and start streaming (20-30 min)

**Total time:** ~2 hours from SSH access to streaming station

### What You Need

**Minimum requirements:**
- Ubuntu 24.04 server with SSH + sudo access
- 2GB RAM, 10GB disk space
- API keys: [Anthropic Claude](https://console.anthropic.com/) + [Google Gemini](https://ai.google.dev/)
- Your coordinates (for weather)
- Music files (20+ tracks minimum)

### Default vs Custom

**Out of the box:** Tropical island radio (DJ Coco on WKRP Coconut Island 🌴)

**Customize everything:** Station name, personality, world-building, news feeds, voice, energy level, humor style - 100+ configuration options.

**Example custom station:** [LAST BYTE RADIO](https://radio.clintecker.com) - Cyberpunk dystopia broadcasting from post-collapse Chicago

---

## Documentation

### Core Guides

- **[VM Setup Guide](docs/VM_SETUP.md)** - Ubuntu server setup from scratch
- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete reference for all 100+ environment variables
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deploy code and start streaming
- **[Administration Guide](docs/ADMINISTRATION.md)** - Day-to-day operations and maintenance *(coming soon)*
- **[Scripts Reference](docs/SCRIPTS.md)** - What each script does *(coming soon)*
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Comprehensive issue diagnosis *(coming soon)*

### Additional Documentation

- **[Adding Music](docs/ADDING_MUSIC.md)** - Music library management
- **[Now Playing API](docs/NOW_PLAYING_API.md)** - Metadata API documentation

---

## Station Personality Examples

Everything is configured via `.env` file. No code changes needed.

**Default (Tropical Island):**
- 🌴 WKRP Coconut Island, DJ Coco
- Vibe: Laid-back, friendly, warm, island time
- News: NPR feed with tropical framing
- Energy: 5/10 (chill vibes)

**Example: LAST BYTE RADIO** (`.env.lastbyte`)
- 🤖 Broadcasting from post-capitalist Chicago wasteland
- Vibe: Witty, darkly humorous, slightly unhinged, defiant
- News: Local + tech feeds with cyberpunk dystopian framing
- Hallucinated: Corp collapses, power grid failures, underground mesh networks
- Energy: 8/10 (high energy, fast-paced)

**Other Ideas:**
- Jazz lounge: Smooth, sophisticated, late-night vibes
- College radio: Chaotic, enthusiastic, DIY energy
- Pirate station: Rebellious, anti-establishment, underground
- News talk: Serious, journalistic, minimal music

**Configure yours:** See [Configuration Guide](docs/CONFIGURATION.md)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI RADIO STATION                           │
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

See [VM Setup Guide](docs/VM_SETUP.md) for complete system requirements and installation instructions.

**Quick summary:**
- Ubuntu 24.04 LTS server
- 2GB RAM, 10GB disk space
- Python 3.12+, Liquidsoap 2.0+, Icecast2, FFmpeg
- API keys: Anthropic Claude + Google Gemini

## Installation

Complete installation instructions are in the core guides. Follow them in order:

1. **[VM Setup](docs/VM_SETUP.md)** - Install system packages and prepare Ubuntu server
2. **[Configuration](docs/CONFIGURATION.md)** - Create `.env` file and customize your station
3. **[Deployment](docs/DEPLOYMENT.md)** - Deploy code, prepare assets, install services

**First time?** Start with [VM Setup](docs/VM_SETUP.md).

## Configuration

All station configuration is done via `.env` file - no code changes needed!

**Configure 100+ settings including:**
- Station identity (name, location, personality)
- API keys (Claude for scripts, Gemini/OpenAI for voice)
- World-building (cyberpunk dystopia? Tropical island? Jazz lounge?)
- Announcer personality (energy level, vibe, humor style)
- News sources (RSS feeds + hallucinated content)
- Audio timing (crossfades, bed volumes, break scheduling)

See [Configuration Guide](docs/CONFIGURATION.md) for complete reference.

### Station Scheduling

| Service | Timing | Purpose |
|---------|--------|---------|
| Music Enqueue | Every 2 minutes | Maintains 20-track buffer in queue |
| Station IDs | :15, :30, :45 | Scheduled at :14, :29, :44; plays at track boundary |
| Top-of-Hour Breaks | :00 | News + weather, scheduled at :59 |
| Now Playing Export | Every 10 seconds | Updates web interface |

Modify timing in the corresponding `systemd/*.timer` files.

## Usage

### Quick Commands

```bash
# Check stream status
sudo systemctl status ai-radio-liquidsoap

# View real-time logs
sudo journalctl -u ai-radio-liquidsoap -f

# Check what's queued
echo "music.queue" | nc -U /run/liquidsoap/radio.sock

# Skip current track
echo "music.skip" | nc -U /run/liquidsoap/radio.sock
```

### Stream URLs

- **Stream:** `http://your-server:8000/radio`
- **M3U Playlist:** `http://your-server/stream.m3u`
- **Web Player:** `http://your-server/` (if nginx configured)

### Browse Database (TUI)

Beautiful terminal UI for browsing your music library and play history:

```bash
# Sync database from production
./scripts/sync_db.sh

# Launch TUI
go run ./cmd/radiotui
```

**TUI Controls:** `1-4` switch views • `Tab` cycle sort • `↑/↓` navigate • `Enter` details • `q` quit

### Day-to-Day Operations

For service management, manual queue control, log monitoring, and maintenance tasks, see [Administration Guide](docs/ADMINISTRATION.md) *(coming soon)*.

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

**Quick checks:**
- Stream not working? Check `sudo systemctl status ai-radio-liquidsoap`
- No music playing? Verify music is ingested: `ls /srv/ai_radio/assets/music/`
- Breaks not playing? Check API keys in `.env`

For comprehensive troubleshooting including service diagnostics, queue management, API issues, and permission problems, see [Troubleshooting Guide](docs/TROUBLESHOOTING.md) *(coming soon)*.

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

**Build your own autonomous radio station. Configure it your way. 📻**
