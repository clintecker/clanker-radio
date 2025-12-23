# Deployment Guide

**Purpose:** Get code from GitHub onto your server and start streaming

**Time estimate:** 20-30 minutes for initial deployment

**Prerequisites:**
- Completed [VM Setup](VM_SETUP.md)
- Completed [Configuration](CONFIGURATION.md)

---

## Overview

This guide covers:
1. Cloning the repository
2. Installing Python dependencies
3. Setting up configuration
4. Preparing assets (music, station IDs)
5. Installing systemd services
6. Starting the stream
7. Verification

**Two deployment scenarios:**
- **Initial deployment** - First time setup (this guide)
- **Updates** - Updating existing installation (see [Administration](ADMINISTRATION.md))

---

## Initial Deployment

### 1. Clone Repository

```bash
# Go to base directory
cd /srv/ai_radio

# Clone the repository
git clone https://github.com/clintecker/clanker-radio.git .

# Or if directory already exists:
git clone https://github.com/clintecker/clanker-radio.git /tmp/clanker-radio
cp -r /tmp/clanker-radio/* /srv/ai_radio/
rm -rf /tmp/clanker-radio
```

**What you're getting:**
- `src/ai_radio/` - Python package
- `scripts/` - Operational scripts
- `config/` - Liquidsoap configuration
- `systemd/` - Service definitions
- `nginx/` - Web frontend
- `docs/` - Documentation (you're reading it!)

### 2. Python Environment Setup

```bash
cd /srv/ai_radio

# Create virtual environment with uv
uv venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies from pyproject.toml
uv pip install -e .

# Verify installation
python -c "import ai_radio; print('✓ Package installed')"
```

**What gets installed:**
- `anthropic` - Claude API client
- `httpx` - HTTP requests for APIs
- `pydantic-settings` - Configuration management
- `feedparser` - RSS feed parsing
- Other dependencies (see `pyproject.toml`)

### 3. Configuration

```bash
# Copy example config
cp .env.example .env

# Edit with your settings
nano .env
```

**Required changes:**
1. `RADIO_LLM_API_KEY` - Your Anthropic API key
2. `RADIO_GEMINI_API_KEY` - Your Gemini API key
3. `RADIO_STATION_LAT` / `RADIO_STATION_LON` - Your coordinates
4. `RADIO_STATION_NAME` - Your station name

See [Configuration Guide](CONFIGURATION.md) for complete details.

**Icecast configuration:**

Edit Icecast config with your source password:

```bash
# Edit Icecast config
sudo nano /etc/icecast2/icecast.xml

# Change <source-password> to a strong password
# Save the password - you'll need it for Liquidsoap
```

**Liquidsoap configuration:**

The Liquidsoap config (`config/radio.liq`) reads from your `.env` file, but it also needs the Icecast source password:

```bash
# Edit radio.liq
nano config/radio.liq

# Find the output.icecast section and update password:
# password = "YOUR_ICECAST_SOURCE_PASSWORD"
```

### 4. Directory Structure

Verify all required directories exist:

```bash
cd /srv/ai_radio

# These should have been created during VM setup
ls -la assets/music     # Music library
ls -la assets/breaks    # Generated breaks
ls -la assets/bumpers   # Station IDs
ls -la assets/beds      # Background music for breaks
ls -la assets/safety    # Emergency fallback audio
ls -la public           # Web frontend
ls -la db               # Database location
ls -la logs             # Log files
ls -la state            # Runtime state
ls -la tmp              # Temporary files

# Create any missing directories
mkdir -p assets/{music,breaks,bumpers,beds,safety}
mkdir -p public db logs state tmp
```

### 5. Asset Preparation

#### Music Library

You need music before the station can play anything:

```bash
cd /srv/ai_radio

# Copy your music files to assets/music/
# Supported formats: MP3, FLAC, OGG, OPUS, M4A

# Example: Copy from local directory
scp ~/my_music/*.mp3 yourserver:/srv/ai_radio/assets/music/

# Ingest music into database
source .venv/bin/activate
python scripts/ingest_music.py

# Verify ingestion
sqlite3 db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE source='music';"
# Should show number of tracks
```

**Music requirements:**
- At least 20 tracks (more is better)
- Supported audio formats
- Reasonable quality (128kbps+ MP3 or equivalent)

**Don't have music?** See [docs/ADDING_MUSIC.md](ADDING_MUSIC.md) for free/legal sources.

#### Station IDs

Station IDs are short audio clips that identify your station. You can:

**Option A: Generate your own** (requires TTS setup):
```bash
# Generate 15 station IDs
source .venv/bin/activate
python scripts/generate_station_ids.py --count 15

# They'll be saved to assets/bumpers/
```

**Option B: Use pre-recorded audio:**
```bash
# Copy your pre-recorded station IDs
cp ~/my_station_ids/*.mp3 /srv/ai_radio/assets/bumpers/

# Name them: station_id_01.mp3, station_id_02.mp3, etc.
```

**Option C: Skip for now:**

Station IDs are optional for initial testing. The station will work without them, though it won't be FCC compliant (US) and won't have that professional touch.

#### Background Beds

Background music for breaks (instrumental tracks):

```bash
# Copy instrumental tracks for break backgrounds
cp ~/instrumental_music/*.mp3 /srv/ai_radio/assets/beds/

# Need at least 3-5 tracks
# Recommended: calm, neutral instrumental music
```

**Don't have beds?** You can disable them by editing `config/radio.liq` and commenting out the bed source, or just skip breaks initially.

#### Safety Audio

Fallback audio for when everything goes wrong:

```bash
# Create or copy a safety message
# This plays when the music queue is empty and breaks fail
cp ~/emergency_fallback.mp3 /srv/ai_radio/assets/safety/emergency.mp3
```

**Don't have safety audio?** Liquidsoap will fall back to silence, which is not ideal but won't crash.

---

## Systemd Services Installation

Install systemd service and timer files:

```bash
cd /srv/ai_radio

# Copy service files
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable ai-radio-liquidsoap.service
sudo systemctl enable ai-radio-break-gen.timer
sudo systemctl enable ai-radio-station-id.timer
sudo systemctl enable ai-radio-export-nowplaying.timer
sudo systemctl enable ai-radio-enqueue-music.timer

# Verify services are present
systemctl list-unit-files | grep ai-radio
```

**Services explained:**

| Service | Type | Purpose | Schedule |
|---------|------|---------|----------|
| ai-radio-liquidsoap | service | Main streaming engine | Always running |
| ai-radio-break-gen | timer+service | Generate news breaks | :00 (hourly) |
| ai-radio-station-id | timer+service | Play station IDs | :15, :30, :45 |
| ai-radio-export-nowplaying | timer+service | Update metadata JSON | Every 10 seconds |
| ai-radio-enqueue-music | timer+service | Manage music queue | Every 5 minutes |

**Why timers instead of cron?**
- Systemd timers are more reliable
- Better logging integration
- Can't run multiple instances (built-in locking)
- Better error handling

---

## Database Initialization

Initialize the SQLite database:

```bash
cd /srv/ai_radio
source .venv/bin/activate

# Run database initialization
python -c "from ai_radio.db_assets import initialize_database; from ai_radio.config import config; initialize_database(config.db_path)"

# Verify tables exist
sqlite3 db/radio.sqlite3 ".tables"
# Should show: assets, play_history
```

---

## Starting the Stream

Now everything is ready. Start the services in order:

### 1. Start Liquidsoap

```bash
# Start the main streaming service
sudo systemctl start ai-radio-liquidsoap

# Check status
sudo systemctl status ai-radio-liquidsoap

# Follow logs (Ctrl+C to exit)
sudo journalctl -u ai-radio-liquidsoap -f
```

**What you should see:**
- Liquidsoap starts successfully
- Connects to Icecast
- Music queue is populated (if music was ingested)
- Stream starts playing

**If it fails:** Check logs for errors. Common issues:
- Missing .env file
- Invalid Icecast password
- No music in queue
- Permission errors

### 2. Start Timers

```bash
# Start all timers
sudo systemctl start ai-radio-break-gen.timer
sudo systemctl start ai-radio-station-id.timer
sudo systemctl start ai-radio-export-nowplaying.timer
sudo systemctl start ai-radio-enqueue-music.timer

# Verify timers are active
systemctl list-timers | grep ai-radio
```

**You should see:**
```
NEXT                        LEFT          LAST PASSED UNIT
Mon 2025-12-23 01:00:00 UTC 15min left    n/a  n/a    ai-radio-break-gen.timer
Mon 2025-12-23 00:45:00 UTC 30s left      n/a  n/a    ai-radio-station-id.timer
Mon 2025-12-23 00:44:40 UTC 10s left      n/a  n/a    ai-radio-export-nowplaying.timer
...
```

### 3. Verify Stream

Check that the stream is accessible:

```bash
# Check Icecast status
curl http://localhost:8000/status-json.xsl | python3 -m json.tool

# Should show stream active with listeners: 0 (until someone connects)
```

Access the stream:
- Web player: `http://your-server-ip/` (or your domain)
- Direct stream: `http://your-server-ip:8000/radio`
- M3U playlist: `http://your-server-ip/stream.m3u`

---

## Web Frontend Deployment

Deploy the web player frontend:

```bash
cd /srv/ai_radio

# Copy frontend files to public directory
cp nginx/index.html public/
cp nginx/stream.m3u public/

# Set permissions
chmod 644 public/*

# Configure Nginx
sudo cp nginx/radio.conf /etc/nginx/sites-available/radio
sudo ln -s /etc/nginx/sites-available/radio /etc/nginx/sites-enabled/

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Verify frontend is accessible
curl http://localhost/
```

**Nginx configuration** serves:
- `/` - Web player (index.html)
- `/stream.m3u` - M3U playlist
- `/now_playing.json` - Current track metadata
- `/radio` - Proxies to Icecast (optional)

---

## Deployment Script (for updates)

For future updates, use the deployment script:

```bash
cd /srv/ai_radio

# Deploy everything
./scripts/deploy.sh

# Or deploy specific components
./scripts/deploy.sh frontend  # Just web frontend
./scripts/deploy.sh scripts   # Just Python scripts
./scripts/deploy.sh code      # Just Python package
./scripts/deploy.sh config    # Just Liquidsoap config (prompts to restart)

# Check service health after deployment
./scripts/deploy.sh health
```

**See [Administration Guide](ADMINISTRATION.md)** for detailed update procedures.

---

## Verification Checklist

After deployment, verify everything works:

### Stream Health

```bash
# Liquidsoap running
sudo systemctl status ai-radio-liquidsoap
# Should show: active (running)

# Stream accessible
curl -I http://localhost:8000/radio
# Should show: HTTP/1.0 200 OK

# Music playing
echo "music.queue" | socat - /run/liquidsoap/radio.sock
# Should show: list of track IDs
```

### Timers Active

```bash
# All timers enabled and scheduled
systemctl list-timers | grep ai-radio

# Should show 4 timers with NEXT times
```

### Metadata Updating

```bash
# Now playing JSON exists and is recent
ls -lh /srv/ai_radio/public/now_playing.json
stat /srv/ai_radio/public/now_playing.json | grep Modify
# Modified time should be within last 10 seconds

# Check content
cat /srv/ai_radio/public/now_playing.json | python3 -m json.tool | head -20
```

### Database Populated

```bash
cd /srv/ai_radio

# Check music count
sqlite3 db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE source='music';"
# Should match number of music files ingested

# Check play history
sqlite3 db/radio.sqlite3 "SELECT COUNT(*) FROM play_history;"
# Should show plays (after stream has been running)
```

### Web Frontend

```bash
# Frontend accessible
curl -I http://localhost/
# Should show: HTTP/1.1 200 OK

# Now playing JSON accessible
curl http://localhost/now_playing.json | python3 -m json.tool
```

### All Checks Passing?

✅ **You're streaming!**

Listen to your station:
- Web player: Open `http://your-server-ip/` in a browser
- Direct stream: Open `http://your-server-ip:8000/radio` in a media player
- Mobile: Use the M3U playlist at `http://your-server-ip/stream.m3u`

---

## Troubleshooting Deployment

### Liquidsoap won't start

**Check logs:**
```bash
sudo journalctl -u ai-radio-liquidsoap -n 100
```

**Common issues:**
- `.env` file missing or invalid
- Icecast password mismatch in `radio.liq`
- Music queue empty (no music ingested)
- Socket directory doesn't exist: `sudo mkdir -p /run/liquidsoap`
- Permission issues: `sudo chown -R $(whoami) /srv/ai_radio`

### Music queue empty

```bash
# Check if music was ingested
sqlite3 /srv/ai_radio/db/radio.sqlite3 "SELECT COUNT(*) FROM assets WHERE source='music';"

# If zero, ingest music
cd /srv/ai_radio
source .venv/bin/activate
python scripts/ingest_music.py

# Manually enqueue music
python scripts/enqueue_music.py
```

### Stream unreachable

**Check Icecast:**
```bash
sudo systemctl status icecast2

# If not running:
sudo systemctl start icecast2
```

**Check firewall:**
```bash
sudo ufw status
# Should show port 8000 allowed

# If not:
sudo ufw allow 8000/tcp
```

### Breaks not generating

**Check timer:**
```bash
systemctl status ai-radio-break-gen.timer
# Should show: active (waiting)

# Manually trigger break generation
sudo systemctl start ai-radio-break-gen.service

# Check logs
sudo journalctl -u ai-radio-break-gen.service -n 50
```

**Common issues:**
- API keys not set in `.env`
- Invalid API keys
- Network issues reaching APIs
- Permissions on `/srv/ai_radio/assets/breaks/`

### Metadata not updating

**Check timer:**
```bash
systemctl status ai-radio-export-nowplaying.timer

# Manually trigger export
sudo systemctl start ai-radio-export-nowplaying.service

# Check logs
sudo journalctl -u ai-radio-export-nowplaying.service -n 20
```

**Common issues:**
- Database doesn't exist or is empty
- Liquidsoap socket unreachable
- Permissions on `/srv/ai_radio/public/`

### Web frontend 404

**Check Nginx:**
```bash
sudo systemctl status nginx

# Check if files exist
ls -la /srv/ai_radio/public/
# Should show: index.html, stream.m3u, now_playing.json

# Check Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## Post-Deployment Tasks

### 1. Monitor for 24 Hours

Let the station run and monitor logs:

```bash
# Follow all services
sudo journalctl -f | grep ai-radio

# Or individual services
sudo journalctl -u ai-radio-liquidsoap -f
sudo journalctl -u ai-radio-break-gen.service -f
```

**What to look for:**
- Breaks generating successfully
- Station IDs playing at :15, :30, :45
- Music queue staying full
- No errors in logs

### 2. Test Break Generation

Manually trigger a break to verify API integration:

```bash
cd /srv/ai_radio
source .venv/bin/activate

# Generate a test break
python scripts/generate_break.py

# Listen to it
ls -lt assets/breaks/ | head -5
# Play the most recent break file with a media player
```

### 3. Test Station ID Scheduling

```bash
# Manually queue a station ID
python scripts/schedule_station_id.py

# Check breaks queue
echo "breaks.queue" | socat - /run/liquidsoap/radio.sock
```

### 4. Customize Configuration

Now that everything works, fine-tune your station's personality:

```bash
# Edit configuration
nano .env

# No restart needed - changes apply to next generated break
# To test changes immediately:
python scripts/generate_break.py
```

See [Configuration Guide](CONFIGURATION.md) for detailed customization.

---

## Using Deployment Profiles

For managing multiple station configs (e.g., development vs production):

```bash
# Create a deployment profile
cp .env .env.production
cp .env .env.development

# Deploy with a profile
./scripts/deploy.sh --profile production

# Or use environment-specific config
RADIO_ENV=production ./scripts/deploy.sh
```

**See deployment script source** for advanced usage.

---

## Next Steps

✅ **Station is live!**

Continue to:
- **[Administration Guide](ADMINISTRATION.md)** - Day-to-day operations and maintenance
- **[Scripts Reference](SCRIPTS.md)** - Understand what each script does
- **[Troubleshooting](TROUBLESHOOTING.md)** - Comprehensive issue diagnosis

**Ongoing tasks:**
- Add more music to your library
- Fine-tune personality settings
- Monitor logs for errors
- Customize news feeds
- Generate more station IDs

**Optional enhancements:**
- Set up SSL/TLS for HTTPS
- Configure domain name and DNS
- Add more RSS feeds
- Customize the web frontend
- Set up monitoring/alerting

---

## Deployment Security Checklist

Before exposing your station publicly:

- [ ] Change default passwords (Icecast)
- [ ] Configure firewall (only necessary ports open)
- [ ] Set up SSL/TLS certificates
- [ ] Restrict Icecast admin access
- [ ] Review file permissions (`/srv/ai_radio` should not be world-writable)
- [ ] Consider running services as dedicated user (not root)
- [ ] Keep system packages updated
- [ ] Monitor logs for suspicious activity

**Production deployment?** Consider:
- Load balancer / reverse proxy
- CDN for stream delivery
- Monitoring and alerting
- Backup strategy
- Update/rollback procedures

---

## Additional Resources

- [Liquidsoap Documentation](https://www.liquidsoap.info/doc.html)
- [Icecast Documentation](https://icecast.org/docs/)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Nginx Configuration](https://nginx.org/en/docs/)
