# LAST BYTE RADIO 📻

An AI-powered autonomous radio station that generates news breaks, weather forecasts, and station IDs while streaming music 24/7 from the neon-lit wasteland of Chicago.

## 🎵 Overview

LAST BYTE RADIO is a complete radio automation system featuring:
- **AI-Generated Content**: News breaks with weather forecasts using Google Gemini
- **Voice Synthesis**: Natural-sounding DJ voices via Google TTS
- **Live Streaming**: 24/7 broadcast via Icecast
- **Automated Scheduling**: systemd-managed break generation and content queuing
- **Web Interface**: Cyber-terminal themed player with now playing info
- **Play Tracking**: Complete history of everything that's aired

## ✨ Features

### Content Generation
- **News Breaks**: AI-written news segments generated hourly
- **Weather Reports**: Real-time weather data for Chicago
- **Station IDs**: Automated station identification bumpers
- **Script Writing**: Gemini-powered content creation with voice direction

### Broadcasting
- **Liquidsoap Engine**: Professional-grade audio mixing and streaming
- **Smart Scheduling**: Queue management with priority fallbacks
- **Crossfading**: Smooth transitions between music tracks
- **Audio Normalization**: Consistent volume levels (EBU R128)
- **6-Level Fallback Chain**: Override → Breaks → Music → Beds → Safety → Emergency

### Frontend
- **Real-Time Player**: Stream with play/pause controls
- **Now Playing**: Live metadata display
- **Play Queue**: See what's coming up next
- **Play History**: Recently played tracks with timestamps
- **Responsive Design**: Works on desktop and mobile

### Management
- **Asset Database**: SQLite tracking of all audio content
- **Content-Addressable Storage**: SHA256-based deduplication
- **Automated Deployment**: One-command deployment to production
- **Service Health Monitoring**: Status checks for all components

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LAST BYTE RADIO                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  AI Generation   │    │   Liquidsoap     │    │    Icecast       │
│                  │    │                  │    │                  │
│  Gemini API  ────┼───▶│  Queue Mgmt  ────┼───▶│  MP3 Stream      │
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
│  Assets | Play History | Metadata                               │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (tested on Ubuntu 22.04)
- **Python**: 3.11+
- **Audio**: ffmpeg, liquidsoap 2.0+
- **Streaming**: icecast2
- **Web Server**: nginx

### API Keys
- **Google Gemini API**: For content generation
- **Weather API**: For weather data

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/clanker-radio.git
cd clanker-radio
```

### 2. Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    ffmpeg \
    liquidsoap \
    icecast2 \
    nginx

# Configure Icecast
sudo systemctl enable icecast2
sudo systemctl start icecast2
```

### 3. Install Python Dependencies
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 4. Set Up Directory Structure
```bash
sudo mkdir -p /srv/ai_radio/{assets,logs,scripts,src,config,public}
sudo mkdir -p /srv/ai_radio/assets/{music,breaks,beds,bumpers,safety}
sudo chown -R $USER:$USER /srv/ai_radio
```

### 5. Configure Secrets
```bash
# Create secrets files
echo "YOUR_ICECAST_PASSWORD" > /srv/ai_radio/.icecast_secrets
echo "YOUR_GEMINI_API_KEY" > /srv/ai_radio/.gemini_secrets

# Set proper permissions
chmod 600 /srv/ai_radio/.*_secrets
```

### 6. Configure Environment
Create `/srv/ai_radio/.env`:
```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
WEATHER_API_KEY=your_weather_api_key_here

# Station Info
STATION_NAME="LAST BYTE RADIO"
STATION_LOCATION="Chicago"
STATION_URL="https://radio.clintecker.com"

# Paths
MUSIC_DIR=/srv/ai_radio/assets/music
BREAKS_DIR=/srv/ai_radio/assets/breaks
BEDS_DIR=/srv/ai_radio/assets/beds
BUMPERS_DIR=/srv/ai_radio/assets/bumpers
LOGS_DIR=/srv/ai_radio/logs

# Database
DB_PATH=/srv/ai_radio/db/radio.db
```

### 7. Initialize Database
```bash
cd /srv/ai_radio
uv run python -c "
from pathlib import Path
import sqlite3
from ai_radio.config import get_db_path
from ai_radio.database import init_db

db_path = get_db_path()
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(db_path)
init_db(conn)
conn.close()
print(f'Database initialized at {db_path}')
"
```

### 8. Deploy Services
```bash
# Copy systemd units
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Start core services
sudo systemctl enable --now ai-radio-liquidsoap.service
sudo systemctl enable --now ai-radio-enqueue.timer
sudo systemctl enable --now ai-radio-break-scheduler.service
sudo systemctl enable --now ai-radio-export-nowplaying.timer
sudo systemctl enable --now ai-radio-schedule-station-id.timer
```

### 9. Configure Nginx
```bash
# Copy nginx configuration
sudo cp nginx/radio.conf /etc/nginx/sites-available/
sudo cp nginx/now_playing.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/radio.conf /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/now_playing.conf /etc/nginx/sites-enabled/

# Copy frontend
sudo cp nginx/index.html /srv/ai_radio/public/

# Reload nginx
sudo systemctl reload nginx
```

## 📁 Directory Structure

```
/srv/ai_radio/
├── assets/           # Audio files
│   ├── music/       # Music library (MP3/FLAC)
│   ├── breaks/      # Generated news breaks
│   ├── beds/        # Background music beds
│   ├── bumpers/     # Station ID bumpers
│   └── safety/      # Emergency/safety content
├── config/          # Configuration files
│   └── radio.liq    # Liquidsoap script
├── db/              # Database files
│   └── radio.db     # SQLite database
├── logs/            # Log files
│   ├── liquidsoap.log
│   ├── enqueue.log
│   └── breaks.log
├── public/          # Web frontend
│   ├── index.html
│   └── now_playing.json
├── scripts/         # Python scripts
│   ├── enqueue_music.py
│   ├── schedule_break.py
│   ├── schedule_station_id.py
│   ├── record_play.py
│   └── export_now_playing.py
└── src/             # Python package
    └── ai_radio/
        ├── audio_mixer.py
        ├── break_generator.py
        ├── config.py
        ├── liquidsoap_client.py
        ├── news.py
        ├── script_writer.py
        ├── voice_synth.py
        └── weather.py
```

## 🎮 Usage

### Adding Music
```bash
# Batch ingest music files
./scripts/batch_ingest.sh /path/to/music/folder

# Or manually
uv run python scripts/enqueue_music.py /path/to/song.mp3
```

### Manual Operations
```bash
# Generate and queue a news break immediately
uv run python scripts/schedule_break.py

# Queue a station ID
uv run python scripts/enqueue_station_id.py

# Check queue status
echo "queue.queue" | nc -U /run/liquidsoap/radio.sock

# Skip current track
echo "skip" | nc -U /run/liquidsoap/radio.sock
```

### Service Management
```bash
# Check service health
./scripts/deploy.sh health

# View logs
sudo journalctl -u ai-radio-liquidsoap.service -f
sudo journalctl -u ai-radio-break-scheduler.service -f

# Restart services
sudo systemctl restart ai-radio-liquidsoap.service
```

## 🔧 Development

### Local Development Setup
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ai_radio --cov-report=html

# Linting
uv run ruff check .

# Type checking
uv run mypy src/
```

### Deployment

The project includes an automated deployment script for pushing changes to production:

```bash
# Deploy everything (frontend + scripts + code)
./scripts/deploy.sh

# Deploy specific components
./scripts/deploy.sh frontend  # Just HTML/CSS/JS (2 seconds)
./scripts/deploy.sh scripts   # Python scripts
./scripts/deploy.sh code      # Python package
./scripts/deploy.sh config    # Liquidsoap config (prompts for restart)
./scripts/deploy.sh systemd   # systemd units

# Check service health
./scripts/deploy.sh health
```

See `CLAUDE.md` for detailed deployment documentation.

## 📡 API Endpoints

### Now Playing
```bash
GET /now_playing.json

Response:
{
  "current": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "played_at": "2025-12-22T11:00:00Z",
    "source": "music"
  },
  "next": [
    {
      "title": "Next Song",
      "artist": "Artist",
      "album": "Album"
    }
  ],
  "recent": [
    {
      "title": "Previous Song",
      "artist": "Artist",
      "played_at": "2025-12-22T10:45:00Z",
      "source": "music"
    }
  ]
}
```

### Stream
```bash
# Direct stream URL
http://your-server:8000/radio

# M3U playlist
http://your-server/stream.m3u
```

## 🎛️ Services

### Core Services
- **ai-radio-liquidsoap.service** - Main streaming engine
- **ai-radio-enqueue.service** - Music queue management (oneshot)
- **ai-radio-enqueue.timer** - Triggers music enqueue every 30 seconds

### Content Generation
- **ai-radio-break-scheduler.service** - Top-of-hour news break scheduling
- **ai-radio-schedule-station-id.timer** - Station ID scheduling (every 15 minutes)

### Utilities
- **ai-radio-export-nowplaying.service** - Exports now playing data (oneshot)
- **ai-radio-export-nowplaying.timer** - Updates now playing JSON every 5 seconds

## 🎙️ Audio Processing

### Liquidsoap Configuration
- **Crossfading**: 2-second crossfade between music tracks (fade in/out: 1s each)
- **Normalization**: Target -16 LUFS, gain limits ±6 dB
- **Sample Rate**: 48 kHz
- **Encoding**: MP3 @ 192 kbps, stereo

### Fallback Chain (Priority Order)
1. **Override Queue** - Manual operator control
2. **Break Queue** - News breaks and station IDs
3. **Music Queue** - Regular music rotation
4. **Beds** - Background music loops
5. **Safety Playlist** - Emergency evergreen content
6. **Emergency Tone** - Absolute fallback

All transitions are track-sensitive (wait for tracks to finish) except music-to-music which uses crossfading.

## 🐛 Troubleshooting

### No Audio Streaming
```bash
# Check Liquidsoap is running
sudo systemctl status ai-radio-liquidsoap.service

# Check logs for errors
sudo journalctl -u ai-radio-liquidsoap.service -n 50

# Verify Icecast connection
curl http://localhost:8000/radio

# Check socket permissions
ls -la /run/liquidsoap/radio.sock
```

### Queue Not Filling
```bash
# Check enqueue timer
sudo systemctl status ai-radio-enqueue.timer

# Manually trigger enqueue
sudo systemctl start ai-radio-enqueue.service

# Check for music files
ls -la /srv/ai_radio/assets/music/
```

### Breaks Not Generating
```bash
# Check scheduler service
sudo systemctl status ai-radio-break-scheduler.service

# Check API keys
test -f /srv/ai_radio/.gemini_secrets && echo "Gemini key exists"

# Manually generate a break
uv run python /srv/ai_radio/scripts/schedule_break.py
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R clint:clint /srv/ai_radio/src/ai_radio
sudo chmod -R 755 /srv/ai_radio/src/ai_radio

# Fix socket permissions
sudo chown liquidsoap:liquidsoap /run/liquidsoap/radio.sock
sudo chmod 660 /run/liquidsoap/radio.sock
```

### Frontend Not Updating
```bash
# Check export timer
sudo systemctl status ai-radio-export-nowplaying.timer

# Verify JSON file
cat /srv/ai_radio/public/now_playing.json

# Check nginx serving
curl http://localhost/now_playing.json
```

## 📊 Database Schema

### Assets Table
```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,              -- SHA256 hash
    path TEXT UNIQUE NOT NULL,        -- File path
    kind TEXT NOT NULL,               -- music/break/bed/bumper/safety
    duration_sec REAL NOT NULL,       -- Duration in seconds
    loudness_lufs REAL,               -- Integrated loudness (EBU R128)
    true_peak_dbtp REAL,              -- True peak level
    energy_level INTEGER,             -- 0-100 scale
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

## 🔐 Security Notes

- **Secrets**: Never commit `*_secrets` files to git
- **API Keys**: Store in environment variables or secret files with 600 permissions
- **Database**: SQLite file should be readable only by radio user
- **Socket**: Liquidsoap socket should have 660 permissions

## 📝 License

[Add your license here]

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 🙏 Credits

Built with:
- [Liquidsoap](https://www.liquidsoap.info/) - Audio streaming engine
- [Google Gemini](https://ai.google.dev/) - AI content generation
- [Google Cloud TTS](https://cloud.google.com/text-to-speech) - Voice synthesis
- [Icecast](https://icecast.org/) - Streaming server
- [Python](https://www.python.org/) - Everything else

## 📞 Support

For issues and questions:
- GitHub Issues: [Your repo URL]
- Documentation: See `docs/` directory

---

Broadcasting from the neon-lit wasteland of Chicago 🌃
