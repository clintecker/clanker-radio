# Phase 1: Core Infrastructure - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish 24/7 Icecast streaming with Liquidsoap playout engine and basic fallback chain

**Architecture:** Install and configure Icecast2 as the streaming server, Liquidsoap as the playout engine with a basic fallback chain (music queue → evergreen playlist → safety bumper). Create systemd services for both with auto-restart on failure. Deploy to Proxmox VM with Tailscale + Cloudflared for public access.

**Tech Stack:** Ubuntu 22.04+, Icecast2, Liquidsoap 2.2+, systemd, Tailscale, Cloudflared, cloud-init

---

## Task 1: System Dependencies Installation

**Files:**
- None (system packages)

**Step 1: Update package cache**

Run:
```bash
sudo apt-get update
```

Expected: Package lists updated

**Step 2: Install Icecast2**

Run:
```bash
sudo apt-get install -y icecast2
```

Expected: Icecast2 installed

**Step 3: Install Liquidsoap dependencies**

Run:
```bash
sudo apt-get install -y \
  opam \
  m4 \
  pkg-config \
  libpcre3-dev \
  libssl-dev \
  libmad0-dev \
  libmp3lame-dev \
  libtag1-dev \
  libfaad-dev \
  libflac-dev \
  libvorbis-dev \
  libsamplerate0-dev \
  libgd-dev \
  ffmpeg
```

Expected: All dependencies installed

**Step 4: Install Liquidsoap via OPAM**

Run:
```bash
sudo -u ai-radio bash << 'OPAM_SETUP'
opam init --disable-sandboxing -y
eval $(opam env)
opam install -y liquidsoap
OPAM_SETUP
```

Expected: Liquidsoap installed for ai-radio user

**Step 5: Verify Liquidsoap installation**

Run:
```bash
sudo -u ai-radio bash -c 'eval $(opam env) && liquidsoap --version'
```

Expected output (version 2.2.x or higher):
```
Liquidsoap 2.2.x
```

**Step 6: Install audio tools for loudness normalization**

Run:
```bash
sudo apt-get install -y ffmpeg python3-pip
sudo pip3 install ffmpeg-normalize
```

Expected: ffmpeg-normalize installed globally

**Step 7: Verify ffmpeg-normalize**

Run:
```bash
ffmpeg-normalize --version
```

Expected: Version number displayed

---

## Task 2: Icecast Configuration

**Files:**
- Modify: `/etc/icecast2/icecast.xml`
- Create: `/etc/default/icecast2`

**Step 1: Backup original Icecast configuration**

Run:
```bash
sudo cp /etc/icecast2/icecast.xml /etc/icecast2/icecast.xml.orig
```

Expected: Backup created

**Step 2: Create Icecast configuration**

Create file `/etc/icecast2/icecast.xml`:
```xml
<icecast>
    <location>Earth</location>
    <admin>radio@clintecker.com</admin>

    <limits>
        <clients>100</clients>
        <sources>2</sources>
        <queue-size>524288</queue-size>
        <client-timeout>30</client-timeout>
        <header-timeout>15</header-timeout>
        <source-timeout>10</source-timeout>
        <burst-on-connect>1</burst-on-connect>
        <burst-size>65535</burst-size>
    </limits>

    <authentication>
        <source-password>CHANGE_THIS_SOURCE_PASSWORD</source-password>
        <relay-password>CHANGE_THIS_RELAY_PASSWORD</relay-password>
        <admin-user>admin</admin-user>
        <admin-password>CHANGE_THIS_ADMIN_PASSWORD</admin-password>
    </authentication>

    <hostname>radio.clintecker.com</hostname>

    <listen-socket>
        <port>8000</port>
        <bind-address>127.0.0.1</bind-address>
    </listen-socket>

    <mount type="normal">
        <mount-name>/stream</mount-name>
        <charset>UTF-8</charset>
    </mount>

    <fileserve>1</fileserve>

    <paths>
        <basedir>/usr/share/icecast2</basedir>
        <logdir>/var/log/icecast2</logdir>
        <webroot>/usr/share/icecast2/web</webroot>
        <adminroot>/usr/share/icecast2/admin</adminroot>
        <alias source="/" destination="/status.xsl"/>
    </paths>

    <logging>
        <accesslog>access.log</accesslog>
        <errorlog>error.log</errorlog>
        <loglevel>3</loglevel>
        <logsize>10000</logsize>
    </logging>

    <security>
        <chroot>0</chroot>
    </security>
</icecast>
```

Run:
```bash
sudo tee /etc/icecast2/icecast.xml << 'EOF'
[content above]
EOF
```

Expected: Icecast configuration created

**Step 3: Enable Icecast2 service**

Edit `/etc/default/icecast2`:
```bash
ENABLE=true
```

Run:
```bash
echo 'ENABLE=true' | sudo tee /etc/default/icecast2
```

Expected: Icecast2 enabled

**Step 4: Set secure permissions on Icecast config**

Run:
```bash
sudo chmod 640 /etc/icecast2/icecast.xml
sudo chown root:icecast /etc/icecast2/icecast.xml
```

Expected: Permissions set

**Step 5: Create Icecast secrets file**

Create file `/srv/ai_radio/.icecast_secrets`:
```bash
ICECAST_SOURCE_PASSWORD=$(openssl rand -base64 32)
ICECAST_RELAY_PASSWORD=$(openssl rand -base64 32)
ICECAST_ADMIN_PASSWORD=$(openssl rand -base64 32)
```

Run:
```bash
sudo -u ai-radio bash << 'SECRETS'
cat > /srv/ai_radio/.icecast_secrets << EOF
ICECAST_SOURCE_PASSWORD=$(openssl rand -base64 32)
ICECAST_RELAY_PASSWORD=$(openssl rand -base64 32)
ICECAST_ADMIN_PASSWORD=$(openssl rand -base64 32)
EOF
chmod 600 /srv/ai_radio/.icecast_secrets
SECRETS
```

Expected: Secrets file created with random passwords

**Step 6: Update Icecast config with generated secrets**

Run:
```bash
sudo bash << 'UPDATE_SECRETS'
source /srv/ai_radio/.icecast_secrets
sed -i "s/CHANGE_THIS_SOURCE_PASSWORD/$ICECAST_SOURCE_PASSWORD/" /etc/icecast2/icecast.xml
sed -i "s/CHANGE_THIS_RELAY_PASSWORD/$ICECAST_RELAY_PASSWORD/" /etc/icecast2/icecast.xml
sed -i "s/CHANGE_THIS_ADMIN_PASSWORD/$ICECAST_ADMIN_PASSWORD/" /etc/icecast2/icecast.xml
UPDATE_SECRETS
```

Expected: Passwords replaced in config

**Step 7: Start Icecast service**

Run:
```bash
sudo systemctl start icecast2
sudo systemctl enable icecast2
```

Expected: Icecast2 started and enabled

**Step 8: Verify Icecast is running**

Run:
```bash
sudo systemctl status icecast2
```

Expected: Service active (running)

**Step 9: Test Icecast status endpoint**

Run:
```bash
curl -s http://127.0.0.1:8000/status-json.xsl | jq .
```

Expected: JSON status response with empty sources array

---

## Task 3: Icecast Log Rotation (OPERATIONAL FIX)

**Files:**
- Create: `/etc/logrotate.d/icecast2`

**Why:** Icecast logs grow unbounded without rotation, leading to disk space issues.

**Step 1: Create logrotate configuration for Icecast**

Create file `/etc/logrotate.d/icecast2`:
```
/var/log/icecast2/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 icecast icecast
    sharedscripts
    postrotate
        systemctl reload icecast2 >/dev/null 2>&1 || true
    endscript
}
```

Run:
```bash
sudo tee /etc/logrotate.d/icecast2 << 'EOF'
/var/log/icecast2/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 icecast icecast
    sharedscripts
    postrotate
        systemctl reload icecast2 >/dev/null 2>&1 || true
    endscript
}
EOF
```

Expected: Logrotate configuration created

**Step 2: Test logrotate configuration**

Run:
```bash
sudo logrotate -d /etc/logrotate.d/icecast2
```

Expected: Dry-run shows rotation would work without errors

**Step 3: Verify permissions**

Run:
```bash
ls -la /etc/logrotate.d/icecast2
```

Expected: `-rw-r--r-- root root`

---

## Task 4: Safety Assets Creation

**Files:**
- Create: `/srv/ai_radio/assets/safety/evergreen.m3u`
- Create: `/srv/ai_radio/assets/safety/hourly_bumper.mp3`
- Create: `/srv/ai_radio/assets/safety/technical_difficulties.mp3`

**Step 1: Create placeholder music tracks**

For testing, we'll create silent audio files. In production, these will be replaced with actual music.

Run:
```bash
# Create 3-minute silence as placeholder music
for i in {1..10}; do
  sudo -u ai-radio ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 180 \
    -c:a libmp3lame -b:a 192k \
    /srv/ai_radio/assets/music/placeholder_$(printf "%02d" $i).mp3 \
    -y
done
```

Expected: 10 placeholder music files created

**Step 2: Normalize placeholder tracks to -18 LUFS**

Run:
```bash
sudo -u ai-radio bash << 'NORMALIZE'
for file in /srv/ai_radio/assets/music/*.mp3; do
  temp_file="${file}.tmp.mp3"
  ffmpeg-normalize "$file" \
    --normalization-type ebu \
    --target-level -18 \
    --true-peak -1 \
    --audio-codec libmp3lame \
    --audio-bitrate 192k \
    --output "$temp_file" \
    --force
  mv "$temp_file" "$file"
done
NORMALIZE
```

Expected: All tracks normalized

**Step 3: Create evergreen playlist**

Run:
```bash
sudo -u ai-radio bash << 'PLAYLIST'
find /srv/ai_radio/assets/music -name "*.mp3" -type f | sort > /srv/ai_radio/assets/safety/evergreen.m3u
PLAYLIST
```

Expected: Playlist file created with all music tracks

**Step 4: Verify playlist**

Run:
```bash
sudo -u ai-radio cat /srv/ai_radio/assets/safety/evergreen.m3u
```

Expected: List of music file paths

**Step 5: Create hourly bumper (station ID)**

Run:
```bash
# Create a simple 10-second station ID beep pattern
sudo -u ai-radio ffmpeg -f lavfi \
  -i "sine=frequency=1000:duration=0.5,sine=frequency=800:duration=0.5,sine=frequency=1000:duration=0.5" \
  -af "volume=-18dB" \
  -c:a libmp3lame -b:a 192k \
  /srv/ai_radio/assets/safety/hourly_bumper.mp3 \
  -y
```

Expected: Bumper audio file created

**Step 6: Create technical difficulties message**

Run:
```bash
# Create a longer station ID / technical difficulties message
sudo -u ai-radio ffmpeg -f lavfi \
  -i "sine=frequency=440:duration=1,sine=frequency=440:duration=1" \
  -af "volume=-18dB" \
  -c:a libmp3lame -b:a 192k \
  /srv/ai_radio/assets/safety/technical_difficulties.mp3 \
  -y
```

Expected: Technical difficulties audio created

**Step 7: Verify safety assets exist**

Run:
```bash
ls -lh /srv/ai_radio/assets/safety/
```

Expected: All three safety files present

---

## Task 5: Liquidsoap Configuration

**Files:**
- Create: `/srv/ai_radio/radio.liq`

**Step 1: Create basic Liquidsoap script**

Create file `/srv/ai_radio/radio.liq`:
```liquidsoap
#!/usr/bin/env liquidsoap

# AI Radio Station - Basic Liquidsoap Configuration
# Phase 1: Core Infrastructure with basic fallback

# Set log level
set("log.level", 3)
set("log.file", true)
set("log.file.path", "/srv/ai_radio/logs/liquidsoap.log")

# Station settings
station_name = "AI Radio Station"
station_description = "24/7 AI-Powered Radio"

# Icecast settings (read source password from secrets file)
icecast_host = "127.0.0.1"
icecast_port = 8000
icecast_password = ref("")

# Read Icecast source password from secrets file
def read_icecast_password() =
  result = list.hd(default="", process.read.lines("bash -c 'source /srv/ai_radio/.icecast_secrets && echo $ICECAST_SOURCE_PASSWORD'"))

  # Validate password was successfully read
  if result == "" then
    log(level=1, "CRITICAL: Failed to read Icecast password from /srv/ai_radio/.icecast_secrets")
    log(level=1, "CRITICAL: Ensure .icecast_secrets exists and ICECAST_SOURCE_PASSWORD is set")
    # Exit with error - cannot continue without password
    exit(1)
  end

  icecast_password := result
  log("Icecast password loaded successfully")
end

# Load password on startup
read_icecast_password()

# Enable telnet server for control
set("server.telnet", true)
set("server.telnet.bind_addr", "127.0.0.1")
set("server.telnet.port", 1234)

# Enable Unix socket for control
set("server.socket", true)
set("server.socket.path", "/run/liquidsoap/radio.sock")
set("server.socket.permissions", 0o660)

# Audio settings
set("frame.audio.samplerate", 44100)
set("frame.audio.channels", 2)

# Create request queues for music
music_queue = request.queue(id="music_queue")

# Create evergreen fallback playlist
evergreen = playlist.safe(
  id="evergreen",
  mode="randomize",
  reload_mode="watch",
  "/srv/ai_radio/assets/safety/evergreen.m3u"
)

# Create safety bumper (plays on repeat if everything else fails)
safety_bumper = single(
  id="safety_bumper",
  "/srv/ai_radio/assets/safety/hourly_bumper.mp3"
)

# Build fallback chain: music queue → evergreen → safety bumper
radio = fallback(
  id="main_fallback",
  track_sensitive=false,
  [
    music_queue,
    evergreen,
    safety_bumper
  ]
)

# Add crossfade between tracks (1.5 seconds)
radio = crossfade(
  duration=1.5,
  radio
)

# Normalize audio to prevent clipping
radio = normalize(
  target=-18.0,
  threshold=-22.0,
  radio
)

# Output to Icecast
output.icecast(
  %mp3(bitrate=192, samplerate=44100, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/stream",
  name=station_name,
  description=station_description,
  genre="Variety",
  url="https://radio.clintecker.com",
  radio
)

# Log startup
log("AI Radio Station started - Phase 1: Core Infrastructure")
log("Fallback chain: music_queue → evergreen → safety_bumper")
log("Telnet control: telnet 127.0.0.1 1234")
log("Unix socket: /run/liquidsoap/radio.sock")
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/radio.liq << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/radio.liq
```

Expected: Liquidsoap script created and executable

**Step 2: Test Liquidsoap configuration syntax**

Run:
```bash
sudo -u ai-radio bash << 'TEST_LIQ'
eval $(opam env)
liquidsoap --check /srv/ai_radio/radio.liq
TEST_LIQ
```

Expected: "No errors found" or no output (success)

---

## Task 6: Liquidsoap Wrapper Script (CRITICAL FIX)

**Files:**
- Create: `/srv/ai_radio/scripts/start-liquidsoap.sh`

**Step 1: Create OPAM environment wrapper script**

This wrapper is **CRITICAL** for systemd integration. Without it, Liquidsoap will fail to start because systemd doesn't load OPAM environment variables.

Create file `/srv/ai_radio/scripts/start-liquidsoap.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Liquidsoap Startup Wrapper
# Initializes OPAM environment before starting Liquidsoap
# CRITICAL: Required for systemd integration

# Load OPAM environment variables
eval $(opam env)

# Verify Liquidsoap is available
if ! command -v liquidsoap &> /dev/null; then
    echo "ERROR: Liquidsoap not found after loading OPAM environment"
    exit 1
fi

# Log startup
echo "[$(date)] Starting Liquidsoap $(liquidsoap --version | head -1)"

# Exec replaces the shell process, preserving proper signal handling for systemd
exec liquidsoap /srv/ai_radio/radio.liq
```

Run:
```bash
sudo mkdir -p /srv/ai_radio/scripts
sudo -u ai-radio tee /srv/ai_radio/scripts/start-liquidsoap.sh << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/scripts/start-liquidsoap.sh
```

Expected: Wrapper script created and executable

**Step 2: Test wrapper script manually**

Run:
```bash
sudo -u ai-radio /srv/ai_radio/scripts/start-liquidsoap.sh --check
```

Expected: Liquidsoap version displayed (will exit quickly in check mode)

---

## Task 7: systemd Service Configuration

**Files:**
- Create: `/etc/systemd/system/ai-radio-icecast.service`
- Create: `/etc/systemd/system/ai-radio-liquidsoap.service`

**Step 1: Create Icecast systemd service override**

We'll use the existing icecast2.service but create an override for consistency.

Run:
```bash
sudo systemctl enable icecast2.service
```

Expected: Icecast2 service enabled

**Step 2: Create Liquidsoap systemd service**

Create file `/etc/systemd/system/ai-radio-liquidsoap.service`:
```ini
[Unit]
Description=AI Radio Station - Liquidsoap Playout Engine
Documentation=https://www.liquidsoap.info/
After=network.target icecast2.service
Requires=icecast2.service
PartOf=ai-radio.target

[Service]
Type=simple
User=ai-radio
Group=ai-radio
WorkingDirectory=/srv/ai_radio

# Create /run/liquidsoap automatically (replaces tmpfiles.d approach)
RuntimeDirectory=liquidsoap
RuntimeDirectoryMode=0755

# Use wrapper script that loads OPAM environment
ExecStart=/srv/ai_radio/scripts/start-liquidsoap.sh

# Restart on failure
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/ai_radio /run/liquidsoap

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-radio-liquidsoap

[Install]
WantedBy=multi-user.target
WantedBy=ai-radio.target
```

Run:
```bash
sudo tee /etc/systemd/system/ai-radio-liquidsoap.service << 'EOF'
[content above]
EOF
```

Expected: Liquidsoap service file created

**Step 3: Create ai-radio.target for grouped control**

Create file `/etc/systemd/system/ai-radio.target`:
```ini
[Unit]
Description=AI Radio Station Services
Documentation=https://github.com/clintecker/clanker-radio
Wants=icecast2.service ai-radio-liquidsoap.service

[Install]
WantedBy=multi-user.target
```

Run:
```bash
sudo tee /etc/systemd/system/ai-radio.target << 'EOF'
[content above]
EOF
```

Expected: Target file created

**Step 4: Reload systemd daemon**

Run:
```bash
sudo systemctl daemon-reload
```

Expected: Daemon reloaded

**Step 5: Enable Liquidsoap service**

Run:
```bash
sudo systemctl enable ai-radio-liquidsoap.service
```

Expected: Service enabled

**Step 6: Enable ai-radio.target**

Run:
```bash
sudo systemctl enable ai-radio.target
```

Expected: Target enabled

**Step 7: Start Liquidsoap service**

Run:
```bash
sudo systemctl start ai-radio-liquidsoap.service
```

Expected: Service started

**Step 8: Verify Liquidsoap is running**

Run:
```bash
sudo systemctl status ai-radio-liquidsoap.service
```

Expected: Service active (running)

**Step 9: Check Liquidsoap logs**

Run:
```bash
sudo journalctl -u ai-radio-liquidsoap.service -n 50 --no-pager
```

Expected: Log output showing "AI Radio Station started"

---

## Task 8: Stream Verification

**Files:**
- None (verification only)

**Step 1: Verify Icecast shows active source**

Run:
```bash
curl -s http://127.0.0.1:8000/status-json.xsl | jq '.icestats.source'
```

Expected: JSON showing /stream mount with listener data

**Step 2: Test stream connectivity**

Run:
```bash
timeout 10 ffmpeg -i http://127.0.0.1:8000/stream -t 5 -f null - 2>&1 | grep -i "Stream"
```

Expected: Stream metadata displayed (MP3, 192kb/s, 44.1kHz)

**Step 3: Verify Unix socket exists and is accessible**

Run:
```bash
ls -l /run/liquidsoap/radio.sock
```

Expected: Socket file owned by ai-radio:ai-radio

**Step 4: Test Liquidsoap telnet interface**

Run:
```bash
echo "help" | nc 127.0.0.1 1234
```

Expected: Help text from Liquidsoap showing available commands

**Step 5: Queue a test track via Liquidsoap**

Run:
```bash
echo "music_queue.push /srv/ai_radio/assets/music/placeholder_01.mp3" | nc 127.0.0.1 1234
```

Expected: "OK" response

**Step 6: Check queue status**

Run:
```bash
echo "music_queue.queue" | nc 127.0.0.1 1234
```

Expected: List showing queued track

**Step 7: Monitor stream for 60 seconds**

Run:
```bash
timeout 60 ffplay -nodisp -autoexit http://127.0.0.1:8000/stream 2>&1 | head -20
```

Expected: Audio playback (if ffplay available) or stream connection success

---

## Task 9: Deployment Configuration (Proxmox + Tailscale + Cloudflared)

**Files:**
- Create: `/srv/ai_radio/deploy/cloud-init.yaml`
- Create: `/srv/ai_radio/deploy/bootstrap.sh`
- Create: `/srv/ai_radio/deploy/tailscale-setup.sh`
- Create: `/srv/ai_radio/deploy/cloudflared-setup.sh`

**Step 1: Create deployment directory**

Run:
```bash
sudo mkdir -p /srv/ai_radio/deploy
sudo chown -R ai-radio:ai-radio /srv/ai_radio/deploy
```

Expected: Deployment directory created

**Step 2: Create cloud-init configuration**

Create file `/srv/ai_radio/deploy/cloud-init.yaml`:
```yaml
#cloud-config
hostname: ai-radio
fqdn: ai-radio.clintecker.com

# User configuration
users:
  - name: clint
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJqfNqZ7F9k0xHH8qR8vF9vYnF5gKGkVxZ9LqN8vZ9LQ clint@example

# Package updates
package_update: true
package_upgrade: true

# Install base packages
packages:
  - git
  - curl
  - wget
  - htop
  - vim
  - tree
  - jq
  - sqlite3
  - build-essential
  - python3
  - python3-pip

# Set timezone
timezone: America/Chicago

# Run bootstrap script on first boot
runcmd:
  - timedatectl set-timezone America/Chicago
  - systemctl enable systemd-timesyncd
  - systemctl start systemd-timesyncd

# Write marker file
write_files:
  - path: /etc/ai-radio-cloud-init-complete
    content: |
      Cloud-init completed at $(date)
    permissions: '0644'
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/deploy/cloud-init.yaml << 'EOF'
[content above]
EOF
```

Expected: Cloud-init configuration created

**Step 3: Create bootstrap deployment script**

Create file `/srv/ai_radio/deploy/bootstrap.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Bootstrap Deployment Script
# Run this on a fresh Ubuntu VM to set up the radio station from this repository

REPO_URL="https://github.com/clintecker/clanker-radio.git"
DEPLOY_DIR="/srv/ai_radio"
LOG_FILE="/var/log/ai-radio-bootstrap.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*"
    exit 1
}

log "=== AI Radio Station Bootstrap Started ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

# Update system
log "Updating system packages..."
apt-get update || error "Failed to update package lists"

# Install git if not present
if ! command -v git &> /dev/null; then
    log "Installing git..."
    apt-get install -y git || error "Failed to install git"
fi

# Clone repository
if [ ! -d "$DEPLOY_DIR" ]; then
    log "Cloning repository to $DEPLOY_DIR..."
    git clone "$REPO_URL" "$DEPLOY_DIR" || error "Failed to clone repository"
else
    log "Repository already exists at $DEPLOY_DIR, pulling latest..."
    cd "$DEPLOY_DIR"
    git pull || error "Failed to pull latest changes"
fi

# Check if Phase 0 plan exists
PHASE_0_PLAN="$DEPLOY_DIR/docs/plans/2025-12-18-phase-0-foundation.md"
if [ ! -f "$PHASE_0_PLAN" ]; then
    error "Phase 0 plan not found at $PHASE_0_PLAN"
fi

log "Phase 0 plan found: $PHASE_0_PLAN"
log "Bootstrap complete. Next steps:"
log "1. Review and execute Phase 0 tasks"
log "2. Execute Phase 1 tasks"
log "3. Set up Tailscale: $DEPLOY_DIR/deploy/tailscale-setup.sh"
log "4. Set up Cloudflared: $DEPLOY_DIR/deploy/cloudflared-setup.sh"
log ""
log "=== AI Radio Station Bootstrap Complete ==="
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/deploy/bootstrap.sh << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/deploy/bootstrap.sh
```

Expected: Bootstrap script created and executable

**Step 4: Create Tailscale setup script**

Create file `/srv/ai_radio/deploy/tailscale-setup.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Tailscale Setup
# Connects the VM to CLiNT's Tailscale network for secure access

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

log "=== Tailscale Setup Started ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

# Install Tailscale
if ! command -v tailscale &> /dev/null; then
    log "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh || error "Failed to install Tailscale"
else
    log "Tailscale already installed"
fi

# Check if already authenticated
if tailscale status &> /dev/null; then
    log "Tailscale is already authenticated"
    tailscale status
else
    log "Starting Tailscale authentication..."
    log "Run: sudo tailscale up --hostname=ai-radio"
    log "Then visit the URL to authenticate"
fi

log "=== Tailscale Setup Complete ==="
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/deploy/tailscale-setup.sh << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/deploy/tailscale-setup.sh
```

Expected: Tailscale setup script created

**Step 5: Create Cloudflared setup script**

Create file `/srv/ai_radio/deploy/cloudflared-setup.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Cloudflared Tunnel Setup
# Creates a Cloudflare tunnel for public access to radio.clintecker.com

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

log "=== Cloudflared Setup Started ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

# Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    log "Installing cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    dpkg -i cloudflared-linux-amd64.deb || error "Failed to install cloudflared"
    rm cloudflared-linux-amd64.deb
else
    log "cloudflared already installed"
fi

# Check if already authenticated
if [ -f /root/.cloudflared/cert.pem ]; then
    log "cloudflared is already authenticated"
else
    log "Authenticating cloudflared..."
    log "Run: sudo cloudflared tunnel login"
    log "Then create tunnel: sudo cloudflared tunnel create ai-radio"
fi

# Create tunnel configuration template
TUNNEL_CONFIG="/etc/cloudflared/config.yml"
if [ ! -f "$TUNNEL_CONFIG" ]; then
    log "Creating tunnel configuration template at $TUNNEL_CONFIG"
    mkdir -p /etc/cloudflared
    cat > "$TUNNEL_CONFIG" << 'TUNNEL_EOF'
tunnel: TUNNEL_ID_HERE
credentials-file: /root/.cloudflared/TUNNEL_ID_HERE.json

ingress:
  - hostname: radio.clintecker.com
    service: http://127.0.0.1:8000
  - service: http_status:404
TUNNEL_EOF
    log "Created tunnel config template. Update TUNNEL_ID_HERE with actual tunnel ID."
else
    log "Tunnel configuration already exists at $TUNNEL_CONFIG"
fi

log "=== Cloudflared Setup Complete ==="
log "Next steps:"
log "1. Update $TUNNEL_CONFIG with your tunnel ID"
log "2. Route DNS: cloudflared tunnel route dns ai-radio radio.clintecker.com"
log "3. Start tunnel: sudo cloudflared tunnel run ai-radio"
log "4. Create systemd service: cloudflared service install"
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/deploy/cloudflared-setup.sh << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/deploy/cloudflared-setup.sh
```

Expected: Cloudflared setup script created

**Step 6: Verify all deployment scripts**

Run:
```bash
ls -lh /srv/ai_radio/deploy/
```

Expected: All deployment files present and executable

---

## Task 10: Verification & Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE1_COMPLETE.md`

**Step 1: Run comprehensive verification**

Run:
```bash
#!/bin/bash
echo "=== Phase 1 Verification ==="
echo ""

echo "1. Icecast Status:"
systemctl is-active icecast2
curl -s http://127.0.0.1:8000/status-json.xsl | jq -r '.icestats.source.mount // "No sources"'
echo ""

echo "2. Liquidsoap Status:"
systemctl is-active ai-radio-liquidsoap
echo "music_queue.queue" | nc -w 1 127.0.0.1 1234 | head -5
echo ""

echo "3. Stream Test:"
timeout 5 ffmpeg -i http://127.0.0.1:8000/stream -f null - 2>&1 | grep -i stream | head -3
echo ""

echo "4. Safety Assets:"
ls -lh /srv/ai_radio/assets/safety/
echo ""

echo "5. Fallback Chain:"
echo "fallback.status" | nc -w 1 127.0.0.1 1234
echo ""

echo "=== Phase 1 Complete ==="
```

Expected: All checks pass

**Step 2: Create Phase 1 completion document**

Create file `/srv/ai_radio/docs/PHASE1_COMPLETE.md`:
```markdown
# Phase 1: Core Infrastructure - COMPLETE

**Completion Date:** 2025-12-18
**Status:** ✅ Operational

## What Was Built

### Always-On Services
- ✅ Icecast2 streaming server (127.0.0.1:8000)
- ✅ Liquidsoap playout engine with basic fallback
- ✅ systemd services with auto-restart
- ✅ ai-radio.target for grouped control

### Fallback Chain
1. Music queue (empty on startup)
2. Evergreen playlist (10 placeholder tracks, randomized)
3. Safety bumper (station ID, loops indefinitely)

### Control Interfaces
- Telnet: `telnet 127.0.0.1 1234`
- Unix socket: `/run/liquidsoap/radio.sock`
- systemd: `sudo systemctl start/stop/status ai-radio.target`

### Safety Assets
- `/srv/ai_radio/assets/safety/evergreen.m3u` - Fallback playlist
- `/srv/ai_radio/assets/safety/hourly_bumper.mp3` - Station ID
- `/srv/ai_radio/assets/safety/technical_difficulties.mp3` - Emergency message

### Deployment Scripts
- `deploy/bootstrap.sh` - Fresh VM setup from repository
- `deploy/tailscale-setup.sh` - Secure access via Tailscale
- `deploy/cloudflared-setup.sh` - Public tunnel to radio.clintecker.com

## Testing the Stream

### Listen locally
```bash
ffplay http://127.0.0.1:8000/stream
```

### Queue a track
```bash
echo "music_queue.push /srv/ai_radio/assets/music/placeholder_01.mp3" | nc 127.0.0.1 1234
```

### Check status
```bash
curl -s http://127.0.0.1:8000/status-json.xsl | jq .
```

## Known Limitations (Phase 1)

- No operator override queue yet (Phase 3)
- No break insertion yet (Phase 3)
- Placeholder music only (Phase 2: real music ingest)
- No AI-generated content yet (Phase 4)
- No automated scheduling yet (Phase 5)

## Next Phase

Proceed to Phase 2: Asset Management (music library ingest + normalization)

## SOW Compliance

- ✅ Section 3: Non-Negotiable #1 - Liquidsoap is the playout engine
- ✅ Section 3: Non-Negotiable #2 - Producer/consumer separation ready
- ✅ Section 3: Non-Negotiable #4 - Evergreen fallback implemented
- ✅ Section 8: Stream encoding (MP3, 192kbps, 44.1kHz, stereo)
- ✅ Section 9: Icecast output + basic fallback chain
- ✅ Section 13: systemd services with auto-restart
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/docs/PHASE1_COMPLETE.md << 'EOF'
[content above]
EOF
```

Expected: Completion document created

---

## Definition of Done

Phase 1 is complete when:

- ✅ Icecast2 installed and streaming
- ✅ Liquidsoap installed and playing audio
- ✅ Basic fallback chain works (queue → evergreen → bumper)
- ✅ Safety assets exist and are normalized
- ✅ systemd services configured and running
- ✅ Services auto-restart on failure
- ✅ Stream accessible at http://127.0.0.1:8000/stream
- ✅ Telnet/Unix socket control interfaces work
- ✅ Deployment scripts created for Proxmox setup
- ✅ Verification tests pass

## SOW Compliance Checklist

- ✅ Section 3: Non-Negotiable #1 (Liquidsoap playout engine)
- ✅ Section 3: Non-Negotiable #2 (Producer/consumer separation architecture ready)
- ✅ Section 3: Non-Negotiable #4 (Evergreen fallback playlist)
- ✅ Section 8: Stream encoding (MP3, 192kbps CBR, 44.1kHz, stereo)
- ✅ Section 9: Icecast output + crossfade + basic fallback
- ✅ Section 13: systemd units with auto-restart
- ✅ Section 14: T6 preparation (services start on boot)

## Next Phase

Proceed to Phase 2: Database & Asset Management (music ingest + normalization)
