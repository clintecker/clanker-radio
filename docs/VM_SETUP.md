# VM Setup Guide

**Target:** Ubuntu 24.04 LTS server with SSH access and sudo privileges

**Time estimate:** 30-45 minutes

**Prerequisites:** You have SSH access to an Ubuntu 24.04 machine with sudo privileges (cloud VM, bare metal, or homelab).

---

## Overview

This guide takes you from a fresh Ubuntu server to a production-ready environment for AI Radio Station. You'll install all required packages, compile Liquidsoap, configure services, and verify everything is ready for code deployment.

**What you'll set up:**
- System packages (Python, FFmpeg, SQLite)
- OPAM (OCaml package manager)
- Liquidsoap (audio streaming engine)
- Icecast2 (HTTP streaming server)
- Nginx (web server and reverse proxy)
- Systemd service infrastructure
- Directory structure and permissions

---

## Prerequisites Verification

Before starting, verify your system meets the requirements:

```bash
# Check OS version (should be Ubuntu 24.04 LTS)
lsb_release -a

# Check available disk space (need at least 10GB free)
df -h /

# Check available memory (need at least 2GB RAM)
free -h

# Verify you have sudo access
sudo whoami  # Should output "root"
```

**Minimum requirements:**
- Ubuntu 24.04 LTS (Noble)
- 2GB RAM (4GB recommended)
- 10GB free disk space (more for music library)
- Network connectivity
- Sudo access

---

## System Package Installation

Update the system and install essential packages:

```bash
# Update package lists
sudo apt update

# Install essential build tools and system packages
sudo apt install -y \
  build-essential \
  git \
  curl \
  wget \
  unzip \
  ca-certificates \
  software-properties-common
```

**What these do:**
- `build-essential` - GCC, Make, and other compilation tools (needed for Liquidsoap)
- `git` - Version control (to clone the repository)
- `curl/wget` - Download tools
- `ca-certificates` - SSL/TLS support

### Python 3.12+

Ubuntu 24.04 ships with Python 3.12, but verify:

```bash
# Check Python version
python3 --version  # Should be 3.12 or higher

# Install Python development headers and pip
sudo apt install -y python3-dev python3-pip python3-venv

# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env  # Add uv to PATH
```

**Why uv?** This project uses `uv` instead of pip/poetry for faster dependency resolution and better reproducibility. It's similar to npm/yarn for JavaScript.

### FFmpeg

FFmpeg handles audio processing and format conversion:

```bash
sudo apt install -y ffmpeg

# Verify installation
ffmpeg -version
```

**Why FFmpeg?** Used for:
- Audio file analysis (duration detection)
- Format conversion (if needed)
- Audio mixing and processing

### SQLite

SQLite stores play history and asset metadata:

```bash
sudo apt install -y sqlite3 libsqlite3-dev

# Verify installation
sqlite3 --version
```

**Why SQLite?** Lightweight, serverless database perfect for this use case. No separate database server to manage.

### Icecast2

Icecast2 is the HTTP streaming server that listeners connect to:

```bash
sudo apt install -y icecast2

# During installation, you'll be prompted for:
# - Hostname: Your server's domain or IP
# - Source password: Set a strong password
# - Relay password: Set a strong password
# - Admin password: Set a strong password

# If you want to reconfigure later:
# sudo dpkg-reconfigure icecast2
```

**Why Icecast?** Industry-standard open source streaming server. Supports multiple listeners, metadata updates, and standard streaming protocols.

**Important:** Save the passwords you set. You'll need the source password for Liquidsoap configuration.

### Nginx

Nginx serves the web frontend and can act as a reverse proxy:

```bash
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Verify it's running
sudo systemctl status nginx
```

**Why Nginx?**
- Serves the web player frontend
- Can handle SSL/TLS termination
- Reverse proxy for Icecast (optional)
- Fast, reliable, low resource usage

---

## OPAM and OCaml Setup

Liquidsoap is written in OCaml and distributed via OPAM (OCaml Package Manager). We need to install OPAM and use it to install Liquidsoap.

```bash
# Install OPAM and OCaml dependencies
sudo apt install -y opam ocaml-native-compilers

# Initialize OPAM (creates ~/.opam)
opam init --auto-setup --yes --disable-sandboxing

# Evaluate OPAM environment
eval $(opam env)

# Create a switch with OCaml 5.2.0
opam switch create 5.2.0 ocaml-base-compiler.5.2.0
eval $(opam env)
```

**What's a "switch"?** An OPAM switch is an isolated OCaml environment (like Python's virtualenv). This ensures Liquidsoap gets the exact OCaml version it needs.

**Why disable sandboxing?** Sandboxing can cause issues in some environments. Disabling it allows OPAM to work reliably.

---

## Liquidsoap Installation

Liquidsoap is the heart of the radio station - it manages audio playback, mixing, and streaming.

### Install System Dependencies

Liquidsoap needs various audio libraries:

```bash
sudo apt install -y \
  libmp3lame-dev \
  libmad0-dev \
  libfaad-dev \
  libflac-dev \
  libogg-dev \
  libvorbis-dev \
  libopus-dev \
  libsamplerate0-dev \
  libsoundtouch-dev \
  libao-dev \
  libasound2-dev \
  libpulse-dev \
  libshout3-dev \
  libssl-dev \
  libsrt-openssl-dev \
  libfdk-aac-dev \
  libtag1-dev \
  libmagic-dev \
  libgd-dev \
  libpcre3-dev
```

**What these are:**
- MP3/FLAC/Vorbis/Opus libraries - Audio codec support
- libshout - Streaming to Icecast
- libssl/libsrt - Network security
- libtag - ID3 tag reading
- libsamplerate/soundtouch - Audio processing

### Install Liquidsoap via OPAM

```bash
# Add external repository for latest Liquidsoap
opam repository add liquidsoap https://github.com/savonet/liquidsoap.git

# Install Liquidsoap with required modules
opam install -y liquidsoap

# This will take 10-20 minutes to compile
# Go get coffee ☕
```

**Why compile from source?** The system package (`apt install liquidsoap`) is often outdated. OPAM gives you the latest stable version with all the features you need.

### Verify Installation

```bash
# Check Liquidsoap version
liquidsoap --version

# Test basic functionality
liquidsoap --check 'output.dummy(sine())'
# Should output "No error found." or similar
```

---

## Directory Structure Setup

Create the directory structure for the radio station:

```bash
# Create base directory
sudo mkdir -p /srv/ai_radio

# Create subdirectories
sudo mkdir -p /srv/ai_radio/{src,scripts,config,assets,public,systemd,logs,db,state,tmp}
sudo mkdir -p /srv/ai_radio/assets/{music,breaks,bumpers,beds,safety}

# Set ownership to your user (replace 'youruser' with your username)
sudo chown -R $(whoami):$(whoami) /srv/ai_radio

# Verify structure
tree -L 2 /srv/ai_radio
```

**Directory purposes:**
- `src/` - Python package code
- `scripts/` - Operational scripts (enqueue, generate breaks, etc.)
- `config/` - Liquidsoap configuration
- `assets/` - Audio files
  - `music/` - Your music library
  - `breaks/` - Generated news/weather breaks
  - `bumpers/` - Station IDs
  - `beds/` - Background music for breaks
  - `safety/` - Emergency fallback audio
- `public/` - Web frontend files
- `systemd/` - Service definition files
- `logs/` - Application logs
- `db/` - SQLite database
- `state/` - Runtime state files
- `tmp/` - Temporary files

**Why /srv/ai_radio?** The `/srv` directory is the standard location for site-specific data served by the system. It keeps your radio station isolated from system files.

---

## Service User Configuration (Optional)

For production deployments, running services as a dedicated user improves security. For development/personal use, you can skip this and run as your regular user.

```bash
# Create dedicated ai-radio user (optional)
sudo useradd -r -s /bin/bash -d /srv/ai_radio -c "AI Radio Station" ai-radio

# Transfer ownership
sudo chown -R ai-radio:ai-radio /srv/ai_radio

# Give your user access to the ai-radio group
sudo usermod -aG ai-radio $(whoami)

# Log out and back in for group changes to take effect
```

**Security note:** Running as a dedicated user limits the blast radius if something goes wrong. But it adds complexity - you'll need `sudo -u ai-radio` for many commands.

**For simplicity:** Most users should skip the dedicated user and just run as themselves.

---

## Firewall Configuration

Allow incoming connections to Icecast and web frontend:

```bash
# Check if UFW is active
sudo ufw status

# If UFW is active, allow required ports
sudo ufw allow 8000/tcp   # Icecast stream
sudo ufw allow 80/tcp     # HTTP (web frontend)
sudo ufw allow 443/tcp    # HTTPS (if using SSL)

# Reload firewall
sudo ufw reload

# Verify rules
sudo ufw status numbered
```

**Port purposes:**
- `8000` - Icecast streaming port (where listeners connect)
- `80` - HTTP web server (frontend)
- `443` - HTTPS web server (SSL)

**If you're not using UFW:** Check your firewall (iptables, cloud provider security groups, etc.) and ensure these ports are open.

---

## SSL/TLS Setup (Optional)

For production deployments with a domain name, you'll want HTTPS. If you're just testing locally, skip this section.

### Prerequisites

- A registered domain name pointing to your server
- Ports 80 and 443 open in firewall

### Install Certbot

```bash
# Install Certbot for Let's Encrypt certificates
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d radio.yourdomain.com

# Follow the prompts to configure HTTPS
# Certbot will automatically configure Nginx
```

**Auto-renewal:** Certbot installs a systemd timer that automatically renews certificates before they expire. Verify with:

```bash
sudo systemctl status certbot.timer
```

---

## Icecast Configuration

Configure Icecast for your station:

```bash
# Edit Icecast config
sudo nano /etc/icecast2/icecast.xml
```

**Key settings to change:**

```xml
<icecast>
  <limits>
    <clients>100</clients>           <!-- Max concurrent listeners -->
    <sources>2</sources>              <!-- Max source connections -->
    <burst-size>65535</burst-size>    <!-- Buffer size -->
  </limits>

  <authentication>
    <!-- Change these passwords! -->
    <source-password>YOUR_SOURCE_PASSWORD</source-password>
    <relay-password>YOUR_RELAY_PASSWORD</relay-password>
    <admin-user>admin</admin-user>
    <admin-password>YOUR_ADMIN_PASSWORD</admin-password>
  </authentication>

  <hostname>radio.yourdomain.com</hostname> <!-- Your domain or IP -->

  <listen-socket>
    <port>8000</port>
  </listen-socket>

  <paths>
    <basedir>/usr/share/icecast2</basedir>
    <logdir>/var/log/icecast2</logdir>
    <webroot>/usr/share/icecast2/web</webroot>
    <adminroot>/usr/share/icecast2/admin</adminroot>
  </paths>
</icecast>
```

**Important:** Save the `source-password` - you'll need it for Liquidsoap configuration.

Restart Icecast to apply changes:

```bash
sudo systemctl restart icecast2
sudo systemctl enable icecast2

# Verify it's running
sudo systemctl status icecast2

# Test by visiting http://your-server-ip:8000 in a browser
# You should see the Icecast status page
```

---

## Liquidsoap Socket Directory

Liquidsoap needs a directory for its Unix socket:

```bash
# Create socket directory
sudo mkdir -p /run/liquidsoap

# Set ownership
sudo chown $(whoami):$(whoami) /run/liquidsoap

# Or if using ai-radio user:
# sudo chown ai-radio:ai-radio /run/liquidsoap
```

**Why a socket?** Scripts communicate with Liquidsoap via a Unix socket to control playback, query queue status, etc. This is more secure than TCP sockets.

**Note:** `/run` is cleared on reboot. The systemd service will recreate this directory automatically.

---

## Python Virtual Environment

Set up Python virtual environment for the radio station code:

```bash
# Go to base directory
cd /srv/ai_radio

# Create virtual environment using uv
uv venv .venv

# Activate it
source .venv/bin/activate

# Install basic dependencies (more will be installed during deployment)
uv pip install anthropic httpx pydantic-settings
```

**Why a virtual environment?** Isolates Python packages from the system Python, preventing version conflicts.

---

## Verification Checklist

Before proceeding to configuration and deployment, verify everything is ready:

```bash
# System packages
python3 --version        # Should be 3.12+
ffmpeg -version          # Should output version info
sqlite3 --version        # Should output version info

# OPAM and Liquidsoap
opam --version           # Should output version info
liquidsoap --version     # Should output version info

# Services
sudo systemctl status icecast2  # Should be active (running)
sudo systemctl status nginx     # Should be active (running)

# Directories
ls -la /srv/ai_radio     # Should show directory structure
ls -la /run/liquidsoap   # Should exist with correct permissions

# Firewall (if using UFW)
sudo ufw status          # Should show ports 8000, 80, 443 allowed

# Python environment
source /srv/ai_radio/.venv/bin/activate
python --version         # Should be 3.12+
```

**All checks passing?** You're ready to move to configuration!

---

## Troubleshooting

### OPAM fails to initialize

**Problem:** `opam init` fails with sandbox errors

**Solution:** Use `--disable-sandboxing` flag:
```bash
opam init --disable-sandboxing --yes --auto-setup
```

### Liquidsoap compilation fails

**Problem:** Missing dependencies or compilation errors

**Solution:** Check you installed all system libraries:
```bash
sudo apt install -y $(cat /dev/stdin <<'EOF'
libmp3lame-dev libmad0-dev libfaad-dev libflac-dev libogg-dev
libvorbis-dev libopus-dev libsamplerate0-dev libsoundtouch-dev
libao-dev libasound2-dev libpulse-dev libshout3-dev libssl-dev
libsrt-openssl-dev libfdk-aac-dev libtag1-dev libmagic-dev
libgd-dev libpcre3-dev
EOF
)
```

### Icecast won't start

**Problem:** `systemctl start icecast2` fails

**Solution:** Check the configuration:
```bash
# Test config syntax
sudo icecast2 -c /etc/icecast2/icecast.xml

# Check logs
sudo journalctl -u icecast2 -n 50
```

Common issues:
- Invalid XML in config file
- Port 8000 already in use
- Permission issues on log directory

### Permission denied errors

**Problem:** Can't write to /srv/ai_radio directories

**Solution:** Fix ownership:
```bash
sudo chown -R $(whoami):$(whoami) /srv/ai_radio
```

### Port 8000 blocked

**Problem:** Can't access http://server-ip:8000

**Solution:** Check firewall:
```bash
# UFW
sudo ufw allow 8000/tcp

# Check if port is listening
sudo netstat -tlnp | grep 8000
```

---

## Next Steps

✅ **VM is ready!**

Now proceed to:
- **[Configuration Guide](CONFIGURATION.md)** - Configure your station's personality and settings
- **[Deployment Guide](DEPLOYMENT.md)** - Deploy the code and start streaming

---

## Additional Resources

- [Liquidsoap Documentation](https://www.liquidsoap.info/doc.html)
- [Icecast Documentation](https://icecast.org/docs/)
- [OPAM Documentation](https://opam.ocaml.org/doc/Usage.html)
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)
