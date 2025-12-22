# AI Radio Station - Claude Development Guide

## Deployment

**CRITICAL**: ALWAYS deploy to `clint@10.10.0.86` (NOT radio.clintecker.com)

### Using the Deploy Script (TESTED & WORKING)

The project includes a fully automated deployment script at `scripts/deploy.sh` that handles:
- ✅ Automatic permission fixing (chown/chmod)
- ✅ Safe staging through home directory
- ✅ Color-coded output (green=success, red=error, yellow=warning)
- ✅ Error handling with automatic rollback
- ✅ Health checks after deployment
- ✅ Per-component deployment options

**Quick Start:**

```bash
# Deploy everything (frontend + scripts + code)
./scripts/deploy.sh

# Deploy only frontend (index.html, stream.m3u)
./scripts/deploy.sh frontend

# Deploy only Python scripts
./scripts/deploy.sh scripts

# Deploy only Python package code
./scripts/deploy.sh code

# Deploy systemd units (requires sudo)
./scripts/deploy.sh systemd
```

**Default behavior**: `./scripts/deploy.sh` deploys frontend, scripts, and code (NOT systemd units)

### Detailed Usage Guide

**Check Service Health:**
```bash
./scripts/deploy.sh health
# Shows color-coded service status:
# - Green ✓ = healthy (running/waiting)
# - Red ✗ = failed
# - Yellow ⚠ = warning/inactive
```

**Deploy Config Changes:**
```bash
./scripts/deploy.sh config
# Prompts: "Restart Liquidsoap? (y/N)"
# Use when you've edited config/radio.liq
```

**Common Workflows:**
- **UI changes** → `./scripts/deploy.sh frontend` (2 seconds, no restart)
- **Python changes** → `./scripts/deploy.sh code` (picks up on next run)
- **Script changes** → `./scripts/deploy.sh scripts` (oneshot services)
- **Full deployment** → `./scripts/deploy.sh` (all three + health check)

**What Each Component Does:**
- `frontend` - Deploys nginx/index.html, sets permissions, no restart needed
- `scripts` - Deploys all scripts/*.py, sets +x, fixes ownership
- `code` - Syncs src/ai_radio/, fixes permissions, no restart needed
- `config` - Deploys radio.liq, prompts for Liquidsoap restart
- `systemd` - Installs .service/.timer files, runs daemon-reload

**After Deployment:**
The script automatically shows service health. Failed oneshot services (like ai-radio-export-nowplaying.service) are normal - the timers trigger them periodically.

### Manual Deployment (if needed)

If the deploy script fails, use manual SCP commands with sudo (files require elevated permissions):

```bash
# Frontend (index.html)
scp nginx/index.html clint@10.10.0.86:/tmp/index.html && \
ssh clint@10.10.0.86 'sudo mv /tmp/index.html /srv/ai_radio/public/index.html && sudo chmod 644 /srv/ai_radio/public/index.html'

# Scripts
scp scripts/*.py clint@10.10.0.86:/tmp/ && \
ssh clint@10.10.0.86 'sudo mv /tmp/*.py /srv/ai_radio/scripts/ && sudo chmod +x /srv/ai_radio/scripts/*.py'

# Python package
rsync -av src/ai_radio/ clint@10.10.0.86:/tmp/ai_radio/ && \
ssh clint@10.10.0.86 'sudo rm -rf /srv/ai_radio/src/ai_radio && sudo mv /tmp/ai_radio /srv/ai_radio/src/'
```

**Note**: All files in `/srv/ai_radio` require sudo permissions to modify.

## Server Details

- **Host**: 10.10.0.86 (internal IP)
- **User**: clint
- **Base Path**: /srv/ai_radio
- **Public Web**: /srv/ai_radio/public
- **Scripts**: /srv/ai_radio/scripts
- **Assets**: /srv/ai_radio/assets
- **Database**: /srv/ai_radio/data/radio.db

## Key Components

### Frontend
- **Location**: `nginx/index.html`
- **Public URL**: https://radio.clintecker.com
- **Features**: Cyber terminal interface, VU meter, matrix rain effects

### Backend Services
- **Liquidsoap**: Manages audio streaming and queues
- **Break Scheduler**: Runs news breaks at :00 (systemd timer)
- **Station ID Scheduler**: Plays random station IDs at :15, :30, :45 (systemd timer)
- **Now Playing Exporter**: Updates JSON every 10 seconds (systemd timer)

### Source Type Detection
- **music**: Regular music tracks from `/srv/ai_radio/assets/music`
- **break**: News breaks from `/srv/ai_radio/assets/breaks`
- **bumper**: Station IDs from `/srv/ai_radio/assets/bumpers`

Station IDs come through the breaks queue but are detected and tagged as "bumper" based on path (`/bumpers/` or `station_id` in filename).

## Station IDs

**IMPORTANT**: We do NOT generate station IDs. We only schedule EXISTING station IDs.

- Station IDs are pre-generated audio files in `/srv/ai_radio/assets/bumpers/`
- The scheduler (`schedule_station_id.py`) picks a RANDOM existing file
- They play at :15, :30, :45 past each hour via systemd timer

## Frontend Styling Modes

The now playing interface changes appearance based on source type:

- **Music** (green phosphor): Default cyber terminal styling
- **Break** (amber/red): News break alert styling with warm glow
- **Bumper** (cyan): Station ID styling with cool glow

## Development Workflow

1. Make code changes locally
2. Test if possible
3. Deploy using `./scripts/deploy.sh [component]`
4. Verify changes on https://radio.clintecker.com
5. Check logs on server if needed: `ssh clint@10.10.0.86 'journalctl -u ai-radio-*'`

## Common Tasks

### Restart Liquidsoap
```bash
ssh clint@10.10.0.86 'sudo systemctl restart ai-radio-liquidsoap'
```

### Check Service Status
```bash
ssh clint@10.10.0.86 'systemctl status ai-radio-*'
```

### View Logs
```bash
ssh clint@10.10.0.86 'journalctl -u ai-radio-liquidsoap -f'
```

### Check Queue Status
```bash
ssh clint@10.10.0.86 'echo "music.queue" | nc -U /run/liquidsoap/radio.sock'
ssh clint@10.10.0.86 'echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock'
```
