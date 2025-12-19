# Phase 3: Liquidsoap Advanced Configuration - Implementation Plan (Adapted for Phase 1 Reality)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build multi-level fallback chain with queue management, break insertion, and operator controls

**Architecture:** Extended Liquidsoap configuration with request.queue sources for runtime control, filesystem watchdog for drop-in files, Unix socket interface for operator commands, and 6-level fallback chain ensuring zero dead air

**Tech Stack:** Liquidsoap 2.4.0, Python 3.11+ with watchdog, Unix sockets, systemd

**Adapted From:** Original Phase 3 plan (2025-12-18), updated for Phase 1 implementation reality

---

## Phase 1 Reality Check

**What exists from Phase 1:**
- Liquidsoap configuration: `/srv/ai_radio/config/radio.liq` (not `/srv/ai_radio/radio.liq`)
- MP3 encoding: `%mp3(bitrate=192, samplerate=44100, stereo=true)` ✓
- Icecast mount: `/radio` (not `/stream`)
- Existing sources: `safety_playlist` and `emergency_tone`
- Normalization: `normalize(target=-18.0, threshold=-40.0)` ✓
- OPAM environment: Requires wrapper script for liquidsoap commands
- Python environment: uv-based, dependencies in pyproject.toml
- Directories: `/srv/ai_radio/assets/safety/` exists

**Key Differences from Original Plan:**
- ✅ Configuration file path: `/srv/ai_radio/config/radio.liq` (not `radio.liq` in root)
- ✅ Mount point: `/radio` (not `/stream`)
- ✅ Safety playlist naming: `safety_playlist` (original uses "evergreen")
- ⚠️ Database schema: Uses 'bed' for asset kind (not 'bumper')
- ⚠️ Unix socket: Need to verify if Phase 1 included this (check config)
- ⚠️ OPAM wrapper: liquidsoap commands need `/srv/ai_radio/scripts/liquidsoap-wrapper.sh`

**SOW Compliance Notes:**
- Database schema CHECK constraint: `('music', 'break', 'bed', 'safety')` - plan references "bumpers" but we'll use 'bed' assets for short station IDs
- Break assets will be kind='break', bumper-style content will be kind='bed'

---

## Task 1: Pre-Flight Verification

**Files:**
- Verify: `/srv/ai_radio/config/radio.liq`
- Verify: `/srv/ai_radio/scripts/liquidsoap-wrapper.sh`

**Step 1: Verify Phase 1 configuration file location**

Run:
```bash
ssh ubuntu@10.10.0.86 "ls -la /srv/ai_radio/config/radio.liq"
```

Expected: File exists, owned by ai-radio

**Step 2: Check for Unix socket configuration**

Run:
```bash
ssh ubuntu@10.10.0.86 "grep -A5 'server.socket' /srv/ai_radio/config/radio.liq"
```

Expected: Either socket configuration exists or returns empty (will add if missing)

**Step 3: Verify OPAM wrapper script exists**

Run:
```bash
ssh ubuntu@10.10.0.86 "cat /srv/ai_radio/scripts/liquidsoap-wrapper.sh"
```

Expected: Wrapper script with OPAM environment setup

**Step 4: Backup current configuration**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /srv/ai_radio/config/radio.liq /srv/ai_radio/config/radio.liq.backup-phase2"
```

Expected: Backup created for rollback safety

---

## Task 2: Python Dependencies for Watchdog

**Files:**
- Modify: `/srv/ai_radio/pyproject.toml`

**Step 1: Add watchdog dependency**

Run:
```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv add watchdog"
```

Expected: watchdog added to dependencies

**Step 2: Verify installation**

Run:
```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv pip list | grep watchdog"
```

Expected: watchdog package shown with version

---

## Task 3: Queue Source Definitions

**Files:**
- Modify: `/srv/ai_radio/config/radio.liq`

**Step 1: Add Unix socket configuration (if missing)**

Check if socket config exists from Step 1. If not present, add to TOP of radio.liq:

```liquidsoap
# ============================================================================
# UNIX SOCKET INTERFACE (Phase 3)
# ============================================================================

# Enable Unix socket for runtime control
settings.server.socket := true
settings.server.socket.path := "/run/liquidsoap/radio.sock"
settings.server.socket.permissions := 0o660

log("Unix socket enabled: /run/liquidsoap/radio.sock")
```

Run (only if socket config missing):
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat > /tmp/socket_config.liq << \"SOCKETEOF\"
# ============================================================================
# UNIX SOCKET INTERFACE (Phase 3)
# ============================================================================

# Enable Unix socket for runtime control
settings.server.socket := true
settings.server.socket.path := \"/run/liquidsoap/radio.sock\"
settings.server.socket.permissions := 0o660

log(\"Unix socket enabled: /run/liquidsoap/radio.sock\")

SOCKETEOF
cat /tmp/socket_config.liq /srv/ai_radio/config/radio.liq > /tmp/radio_new.liq && mv /tmp/radio_new.liq /srv/ai_radio/config/radio.liq'"
```

Expected: Socket configuration added to top of file

**Step 2: Add queue source definitions after socket config**

Add queue definitions (insert after socket config, before existing sources):

```liquidsoap
# ============================================================================
# QUEUE SOURCES (Phase 3)
# ============================================================================

# Level 1: Operator override queue (highest priority)
# Drop-in files for immediate playback (urgent announcements, etc.)
override_queue = request.queue(id="override")
log("Override queue initialized (Level 1)")

# Level 3: Music queue (main content)
# Populated by enqueue service (Phase 5)
music_queue = request.queue(id="music")
log("Music queue initialized (Level 3)")

# Level 2: Break queue (news/weather)
# Populated by content generation service (Phase 4)
break_queue = request.queue(id="breaks")
log("Break queue initialized (Level 2)")
```

Create temporary file and insert:

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat > /tmp/queue_sources.liq << \"QUEUEEOF\"
# ============================================================================
# QUEUE SOURCES (Phase 3)
# ============================================================================

# Level 1: Operator override queue (highest priority)
# Drop-in files for immediate playback (urgent announcements, etc.)
override_queue = request.queue(id=\"override\")
log(\"Override queue initialized (Level 1)\")

# Level 3: Music queue (main content)
# Populated by enqueue service (Phase 5)
music_queue = request.queue(id=\"music\")
log(\"Music queue initialized (Level 3)\")

# Level 2: Break queue (news/weather)
# Populated by content generation service (Phase 4)
break_queue = request.queue(id=\"breaks\")
log(\"Break queue initialized (Level 2)\")

QUEUEEOF
'"
```

Expected: Queue definitions ready to insert

**Step 3: Find insertion point in radio.liq**

Run:
```bash
ssh ubuntu@10.10.0.86 "grep -n 'emergency_tone = single' /srv/ai_radio/config/radio.liq"
```

Expected: Line number where emergency_tone is defined (insert queues BEFORE this)

**Step 4: Insert queue definitions**

This requires manual edit. Create script to insert at proper location:

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c '
# Find the line number for emergency_tone
LINE=\$(grep -n \"emergency_tone = single\" /srv/ai_radio/config/radio.liq | cut -d: -f1)
# Split file at that point and insert queue config
head -n \$((LINE - 1)) /srv/ai_radio/config/radio.liq > /tmp/radio_part1.liq
cat /tmp/queue_sources.liq > /tmp/radio_part2.liq
tail -n +\$LINE /srv/ai_radio/config/radio.liq >> /tmp/radio_part2.liq
cat /tmp/radio_part1.liq /tmp/radio_part2.liq > /srv/ai_radio/config/radio.liq
'"
```

Expected: Queue sources inserted before emergency_tone definition

---

## Task 4: Filesystem Drop-In Monitoring

**Files:**
- Create: `/srv/ai_radio/scripts/watch_drops.py`
- Create: `/etc/systemd/system/ai-radio-watch-drops.service`

**Step 1: Create drops directories**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/drops/processed"
```

Expected: Directories created

**Step 2: Create Python watchdog script**

Create file `/srv/ai_radio/scripts/watch_drops.py`:

```python
#!/usr/bin/env python3
"""AI Radio Station - Drop-in File Watchdog

Monitors /srv/ai_radio/drops/ for new MP3 files and automatically
pushes them to Liquidsoap's override queue via Unix socket.

When a file appears:
1. Wait 1 second (ensure file is fully written)
2. Push to override queue via socket command
3. Move file to processed/ directory
"""

import logging
import socket
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
DROPS_DIR = Path("/srv/ai_radio/drops")
PROCESSED_DIR = DROPS_DIR / "processed"
SOCKET_PATH = "/run/liquidsoap/radio.sock"
SUPPORTED_FORMATS = {".mp3", ".flac", ".wav"}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


class DropInHandler(FileSystemEventHandler):
    """Handle file creation events in drops directory."""

    def on_created(self, event):
        """Process newly created files."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process supported audio formats
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            log.warning(f"Ignoring unsupported file: {file_path.name}")
            return

        # Wait for file to be fully written
        time.sleep(1.0)

        try:
            # Push to Liquidsoap override queue
            self.push_to_queue(file_path)

            # Move to processed directory
            processed_path = PROCESSED_DIR / file_path.name
            file_path.rename(processed_path)
            log.info(f"Moved to processed: {file_path.name}")

        except Exception as e:
            log.error(f"Failed to process {file_path.name}: {e}")

    def push_to_queue(self, file_path: Path):
        """Push file to Liquidsoap override queue via Unix socket."""
        command = f"override.push {file_path}\n"

        try:
            # Connect to Liquidsoap Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKET_PATH)

            # Send command
            sock.sendall(command.encode())

            # Read response
            response = sock.recv(1024).decode().strip()
            sock.close()

            log.info(f"Pushed to override queue: {file_path.name}")
            log.debug(f"Liquidsoap response: {response}")

        except Exception as e:
            raise RuntimeError(f"Socket communication failed: {e}")


def main():
    """Start watchdog monitoring."""
    log.info("Starting drop-in file watchdog")
    log.info(f"Monitoring: {DROPS_DIR}")
    log.info(f"Processed: {PROCESSED_DIR}")
    log.info(f"Socket: {SOCKET_PATH}")

    # Ensure processed directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Start monitoring
    event_handler = DropInHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DROPS_DIR), recursive=False)
    observer.start()

    log.info("Watchdog running (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watchdog")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
```

Write to VM:

Run:
```bash
cat > /tmp/watch_drops.py << 'WATCHEOF'
#!/usr/bin/env python3
"""AI Radio Station - Drop-in File Watchdog

Monitors /srv/ai_radio/drops/ for new MP3 files and automatically
pushes them to Liquidsoap's override queue via Unix socket.

When a file appears:
1. Wait 1 second (ensure file is fully written)
2. Push to override queue via socket command
3. Move file to processed/ directory
"""

import logging
import socket
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
DROPS_DIR = Path("/srv/ai_radio/drops")
PROCESSED_DIR = DROPS_DIR / "processed"
SOCKET_PATH = "/run/liquidsoap/radio.sock"
SUPPORTED_FORMATS = {".mp3", ".flac", ".wav"}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


class DropInHandler(FileSystemEventHandler):
    """Handle file creation events in drops directory."""

    def on_created(self, event):
        """Process newly created files."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process supported audio formats
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            log.warning(f"Ignoring unsupported file: {file_path.name}")
            return

        # Wait for file to be fully written
        time.sleep(1.0)

        try:
            # Push to Liquidsoap override queue
            self.push_to_queue(file_path)

            # Move to processed directory
            processed_path = PROCESSED_DIR / file_path.name
            file_path.rename(processed_path)
            log.info(f"Moved to processed: {file_path.name}")

        except Exception as e:
            log.error(f"Failed to process {file_path.name}: {e}")

    def push_to_queue(self, file_path: Path):
        """Push file to Liquidsoap override queue via Unix socket."""
        command = f"override.push {file_path}\n"

        try:
            # Connect to Liquidsoap Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKET_PATH)

            # Send command
            sock.sendall(command.encode())

            # Read response
            response = sock.recv(1024).decode().strip()
            sock.close()

            log.info(f"Pushed to override queue: {file_path.name}")
            log.debug(f"Liquidsoap response: {response}")

        except Exception as e:
            raise RuntimeError(f"Socket communication failed: {e}")


def main():
    """Start watchdog monitoring."""
    log.info("Starting drop-in file watchdog")
    log.info(f"Monitoring: {DROPS_DIR}")
    log.info(f"Processed: {PROCESSED_DIR}")
    log.info(f"Socket: {SOCKET_PATH}")

    # Ensure processed directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Start monitoring
    event_handler = DropInHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DROPS_DIR), recursive=False)
    observer.start()

    log.info("Watchdog running (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watchdog")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
WATCHEOF

scp /tmp/watch_drops.py ubuntu@10.10.0.86:/tmp/watch_drops.py
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/watch_drops.py /srv/ai_radio/scripts/watch_drops.py && sudo chmod +x /srv/ai_radio/scripts/watch_drops.py"
```

Expected: Watchdog script created and executable

**Step 3: Create systemd service**

Create file `/etc/systemd/system/ai-radio-watch-drops.service`:

```ini
[Unit]
Description=AI Radio Station - Drop-in File Watchdog
After=network.target ai-radio-liquidsoap.service
Requires=ai-radio-liquidsoap.service

[Service]
Type=simple
User=ai-radio
Group=ai-radio
WorkingDirectory=/srv/ai_radio

# Use uv run to execute with proper Python environment
ExecStart=/usr/local/bin/uv run --directory /srv/ai_radio python /srv/ai_radio/scripts/watch_drops.py

# Restart on failure
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-radio-watch-drops

[Install]
WantedBy=multi-user.target
```

Run:
```bash
cat > /tmp/ai-radio-watch-drops.service << 'SERVICEEOF'
[Unit]
Description=AI Radio Station - Drop-in File Watchdog
After=network.target ai-radio-liquidsoap.service
Requires=ai-radio-liquidsoap.service

[Service]
Type=simple
User=ai-radio
Group=ai-radio
WorkingDirectory=/srv/ai_radio

# Use uv run to execute with proper Python environment
ExecStart=/usr/local/bin/uv run --directory /srv/ai_radio python /srv/ai_radio/scripts/watch_drops.py

# Restart on failure
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-radio-watch-drops

[Install]
WantedBy=multi-user.target
SERVICEEOF

scp /tmp/ai-radio-watch-drops.service ubuntu@10.10.0.86:/tmp/ai-radio-watch-drops.service
ssh ubuntu@10.10.0.86 "sudo cp /tmp/ai-radio-watch-drops.service /etc/systemd/system/ai-radio-watch-drops.service"
```

Expected: Service file created

**Step 4: Enable and start watchdog service**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo systemctl daemon-reload && sudo systemctl enable ai-radio-watch-drops.service"
```

Expected: Service enabled (don't start yet - will start after Phase 3 config complete)

---

## Task 5: Force Break Trigger

**Files:**
- Modify: `/srv/ai_radio/config/radio.liq`
- Create: `/srv/ai_radio/scripts/force-break.sh`

**Step 1: Create control directory**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/control"
```

Expected: Directory created

**Step 2: Add force break logic to radio.liq**

Add after queue sources, before fallback chain:

```liquidsoap
# ============================================================================
# FORCE BREAK TRIGGER (Phase 3)
# ============================================================================

# Flag file for forcing immediate break
force_break_flag_file = "/srv/ai_radio/control/force_break"

# Reference to track when flag was set
force_break_ref = ref(false)

# Check if force break flag exists (read-only check)
def check_force_break() =
    if file.exists(force_break_flag_file) then
        force_break_ref := true
        true
    else
        !force_break_ref  # Return current state
    end
end

# Wrapper for break queue with force break support
forced_break_queue = switch(
    id="forced_breaks",
    track_sensitive=true,
    [
        # If force break flag exists, play break immediately
        (check_force_break, break_queue)
    ]
)

# Reset flag when break actually starts playing
forced_break_queue.on_track(fun(m) ->
    if !force_break_ref then
        # Break is now playing, safe to remove flag
        if file.exists(force_break_flag_file) then
            file.remove(force_break_flag_file)
            log("Force break playing, flag file removed")
        end
        force_break_ref := false
    end
)

log("Force break trigger enabled: #{force_break_flag_file}")
```

Create temp file and append:

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat >> /srv/ai_radio/config/radio.liq << \"FORCEEOF\"

# ============================================================================
# FORCE BREAK TRIGGER (Phase 3)
# ============================================================================

# Flag file for forcing immediate break
force_break_flag_file = \"/srv/ai_radio/control/force_break\"

# Reference to track when flag was set
force_break_ref = ref(false)

# Check if force break flag exists (read-only check)
def check_force_break() =
    if file.exists(force_break_flag_file) then
        force_break_ref := true
        true
    else
        !force_break_ref  # Return current state
    end
end

# Wrapper for break queue with force break support
forced_break_queue = switch(
    id=\"forced_breaks\",
    track_sensitive=true,
    [
        # If force break flag exists, play break immediately
        (check_force_break, break_queue)
    ]
)

# Reset flag when break actually starts playing
forced_break_queue.on_track(fun(m) ->
    if !force_break_ref then
        # Break is now playing, safe to remove flag
        if file.exists(force_break_flag_file) then
            file.remove(force_break_flag_file)
            log(\"Force break playing, flag file removed\")
        end
        force_break_ref := false
    end
)

log(\"Force break trigger enabled: #{force_break_flag_file}\")
FORCEEOF
'"
```

Expected: Force break logic added

**Step 3: Create force break operator script**

Create `/srv/ai_radio/scripts/force-break.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Force Break Script
# Creates flag file to trigger immediate break playback

FLAG_FILE="/srv/ai_radio/control/force_break"

# Create flag file
touch "$FLAG_FILE"

echo "Force break triggered. Next available break will play immediately."
echo "Flag file created: $FLAG_FILE"
```

Run:
```bash
cat > /tmp/force-break.sh << 'FORCEEOF'
#!/bin/bash
set -euo pipefail

# AI Radio Station - Force Break Script
# Creates flag file to trigger immediate break playback

FLAG_FILE="/srv/ai_radio/control/force_break"

# Create flag file
touch "$FLAG_FILE"

echo "Force break triggered. Next available break will play immediately."
echo "Flag file created: $FLAG_FILE"
FORCEEOF

scp /tmp/force-break.sh ubuntu@10.10.0.86:/tmp/force-break.sh
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/force-break.sh /srv/ai_radio/scripts/force-break.sh && sudo chmod +x /srv/ai_radio/scripts/force-break.sh"
```

Expected: Script created and executable

---

## Task 6: Multi-Level Fallback Chain

**Files:**
- Modify: `/srv/ai_radio/config/radio.liq`

**Step 1: Create bed/bumpers directory**

Note: Database schema uses 'bed' kind (not 'bumper'), so we'll use beds directory:

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/assets/beds"
```

Expected: Directory created for short station ID content

**Step 2: Add bed source definition**

Add before existing fallback chain:

```liquidsoap
# ============================================================================
# BED PLAYLIST (Phase 3)
# ============================================================================

# Short station ID beds for fallback (level 4)
# These play when music queue is empty but we don't want safety playlist yet
# Note: Database uses 'bed' kind (not 'bumper') per SOW Section 6
beds = playlist(
    id="beds",
    mode="random",
    reload=3600,  # Reload every hour
    "/srv/ai_radio/assets/beds"
)

log("Bed playlist configured (level 4 fallback)")
```

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat >> /srv/ai_radio/config/radio.liq << \"BEDEOF\"

# ============================================================================
# BED PLAYLIST (Phase 3)
# ============================================================================

# Short station ID beds for fallback (level 4)
# These play when music queue is empty but we don'\''t want safety playlist yet
# Note: Database uses '\''bed'\'' kind (not '\''bumper'\'') per SOW Section 6
beds = playlist(
    id=\"beds\",
    mode=\"random\",
    reload=3600,  # Reload every hour
    \"/srv/ai_radio/assets/beds\"
)

log(\"Bed playlist configured (level 4 fallback)\")
BEDEOF
'"
```

Expected: Bed source added

**Step 3: Replace existing fallback chain**

Phase 1 has a simple 2-level fallback. We need to:
1. Comment out old fallback
2. Build new 6-level fallback

Find the existing fallback definition:

Run:
```bash
ssh ubuntu@10.10.0.86 "grep -n 'radio = fallback' /srv/ai_radio/config/radio.liq"
```

Expected: Line number of existing fallback

**Step 4: Comment out old fallback and add new one**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c '
# Comment out old fallback line
sed -i \"s/^radio = fallback(/# PHASE 1 OLD: radio = fallback(/\" /srv/ai_radio/config/radio.liq
sed -i \"s/^  track_sensitive=false,/#   track_sensitive=false,/\" /srv/ai_radio/config/radio.liq
sed -i \"s/^  \\[safety_playlist, emergency_tone\\]/#   [safety_playlist, emergency_tone]/\" /srv/ai_radio/config/radio.liq
sed -i \"s/^)$/#)/\" /srv/ai_radio/config/radio.liq
'"
```

Expected: Old fallback commented out

**Step 5: Add new 6-level fallback chain**

```liquidsoap
# ============================================================================
# MULTI-LEVEL FALLBACK CHAIN (Phase 3)
# ============================================================================

# Priority order (highest to lowest):
# 1. Operator override queue (drop-in files)
# 2. Forced breaks (operator-triggered)
# 3. Music queue (main content)
# 4. Beds (short station IDs when queue is empty)
# 5. Safety playlist (fallback music from Phase 1)
# 6. Emergency tone (last resort, loops forever)

# Build the fallback chain from bottom to top
radio = fallback(
    id="main_fallback",
    track_sensitive=true,  # Wait for track boundaries
    [
        # Level 1 (highest): Operator override
        override_queue,

        # Level 2: Forced breaks
        forced_break_queue,

        # Level 3: Music queue (main content)
        music_queue,

        # Level 4: Beds (station IDs)
        beds,

        # Level 5: Safety playlist (from Phase 1)
        safety_playlist,

        # Level 6 (lowest): Emergency tone (loops forever, never fails)
        emergency_tone
    ]
)

log("Multi-level fallback chain configured (6 levels)")
```

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat >> /srv/ai_radio/config/radio.liq << \"FBEOF\"

# ============================================================================
# MULTI-LEVEL FALLBACK CHAIN (Phase 3)
# ============================================================================

# Priority order (highest to lowest):
# 1. Operator override queue (drop-in files)
# 2. Forced breaks (operator-triggered)
# 3. Music queue (main content)
# 4. Beds (short station IDs when queue is empty)
# 5. Safety playlist (fallback music from Phase 1)
# 6. Emergency tone (last resort, loops forever)

# Build the fallback chain from bottom to top
radio = fallback(
    id=\"main_fallback\",
    track_sensitive=true,  # Wait for track boundaries
    [
        # Level 1 (highest): Operator override
        override_queue,

        # Level 2: Forced breaks
        forced_break_queue,

        # Level 3: Music queue (main content)
        music_queue,

        # Level 4: Beds (station IDs)
        beds,

        # Level 5: Safety playlist (from Phase 1)
        safety_playlist,

        # Level 6 (lowest): Emergency tone (loops forever, never fails)
        emergency_tone
    ]
)

log(\"Multi-level fallback chain configured (6 levels)\")
FBEOF
'"
```

Expected: New 6-level fallback chain added

---

## Task 7: Configuration Validation and Restart

**Files:**
- None (validation only)

**Step 1: Validate Liquidsoap configuration syntax**

Use OPAM wrapper to ensure proper environment:

Run:
```bash
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/liquidsoap-wrapper.sh --check /srv/ai_radio/config/radio.liq"
```

Expected: "No errors found" or equivalent

**Step 2: Restart Liquidsoap service**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo systemctl restart ai-radio-liquidsoap.service"
```

Expected: Service restarts successfully

**Step 3: Verify Liquidsoap is running**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo systemctl status ai-radio-liquidsoap.service"
```

Expected: Active (running)

**Step 4: Check Liquidsoap logs for queue initialization**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo journalctl -u ai-radio-liquidsoap.service --since '1 minute ago' | grep -E '(queue|fallback|socket)'"
```

Expected: Log entries showing queue initialization and fallback chain configuration

**Step 5: Verify Unix socket exists**

Run:
```bash
ssh ubuntu@10.10.0.86 "ls -la /run/liquidsoap/radio.sock"
```

Expected: Socket file exists

**Step 6: Test socket connection**

Run:
```bash
ssh ubuntu@10.10.0.86 "echo 'help' | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock | head -20"
```

Expected: List of available commands including override.push, music.push, breaks.push

---

## Task 8: Start Watchdog Service

**Files:**
- None (service management only)

**Step 1: Start watchdog service**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo systemctl start ai-radio-watch-drops.service"
```

Expected: Service starts

**Step 2: Verify watchdog is running**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo systemctl status ai-radio-watch-drops.service"
```

Expected: Active (running)

**Step 3: Check watchdog logs**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo journalctl -u ai-radio-watch-drops.service --since '1 minute ago'"
```

Expected: "Watchdog running" message, no errors

---

## Task 9: Integration Testing

**Files:**
- Create: `/srv/ai_radio/scripts/test-phase3.sh`

**Step 1: Create Phase 3 test script**

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Phase 3 Integration Tests
# Tests multi-level fallback, queue operations, and control interfaces

echo "=== Phase 3: Liquidsoap Advanced Configuration Tests ==="
echo

# Test 1: Verify Liquidsoap is running
echo "[Test 1] Verify Liquidsoap service is running..."
if systemctl is-active --quiet ai-radio-liquidsoap; then
    echo "  ✓ Liquidsoap service is running"
else
    echo "  ✗ Liquidsoap service is NOT running"
    exit 1
fi

# Test 2: Verify Unix socket exists
echo "[Test 2] Verify Unix socket exists..."
if [ -S "/run/liquidsoap/radio.sock" ]; then
    echo "  ✓ Unix socket exists"
else
    echo "  ✗ Unix socket NOT found"
    exit 1
fi

# Test 3: Test socket connection
echo "[Test 3] Test socket connection..."
if echo "help" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock > /dev/null 2>&1; then
    echo "  ✓ Socket connection successful"
else
    echo "  ✗ Socket connection failed"
    exit 1
fi

# Test 4: Verify queue sources are initialized
echo "[Test 4] Verify queue sources..."
QUEUES=$(echo "help" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock | grep -E "(override|music|breaks)" | wc -l)
if [ "$QUEUES" -ge 3 ]; then
    echo "  ✓ All queue sources detected (found $QUEUES)"
else
    echo "  ✗ Missing queue sources (found $QUEUES, expected ≥3)"
    exit 1
fi

# Test 5: Verify drops directory monitoring
echo "[Test 5] Verify drops directory..."
if [ -d "/srv/ai_radio/drops/processed" ]; then
    echo "  ✓ Drops directory structure exists"
else
    echo "  ✗ Drops directory structure missing"
    exit 1
fi

# Test 6: Verify watchdog service
echo "[Test 6] Verify watchdog service..."
if systemctl is-active --quiet ai-radio-watch-drops; then
    echo "  ✓ Watchdog service is running"
else
    echo "  ✗ Watchdog service is NOT running"
    exit 1
fi

# Test 7: Verify control directory
echo "[Test 7] Verify control directory..."
if [ -d "/srv/ai_radio/control" ]; then
    echo "  ✓ Control directory exists"
else
    echo "  ✗ Control directory missing"
    exit 1
fi

# Test 8: Test force break script
echo "[Test 8] Test force break script..."
if [ -x "/srv/ai_radio/scripts/force-break.sh" ]; then
    echo "  ✓ Force break script is executable"
else
    echo "  ✗ Force break script missing or not executable"
    exit 1
fi

# Test 9: Verify stream is broadcasting
echo "[Test 9] Verify stream is broadcasting..."
if curl -s -I http://127.0.0.1:8000/radio | grep -q "200 OK"; then
    echo "  ✓ Stream is broadcasting"
else
    echo "  ✗ Stream is NOT broadcasting"
    exit 1
fi

# Test 10: Verify fallback chain status
echo "[Test 10] Check fallback chain status..."
if echo "main_fallback.status" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock > /dev/null 2>&1; then
    echo "  ✓ Fallback chain is operational"
else
    echo "  ✗ Fallback chain query failed"
    exit 1
fi

echo
echo "=== All Phase 3 Tests Passed ✓ ==="
```

Write to VM:

Run:
```bash
cat > /tmp/test-phase3.sh << 'TESTEOF'
#!/bin/bash
set -euo pipefail

# AI Radio Station - Phase 3 Integration Tests
# Tests multi-level fallback, queue operations, and control interfaces

echo "=== Phase 3: Liquidsoap Advanced Configuration Tests ==="
echo

# Test 1: Verify Liquidsoap is running
echo "[Test 1] Verify Liquidsoap service is running..."
if systemctl is-active --quiet ai-radio-liquidsoap; then
    echo "  ✓ Liquidsoap service is running"
else
    echo "  ✗ Liquidsoap service is NOT running"
    exit 1
fi

# Test 2: Verify Unix socket exists
echo "[Test 2] Verify Unix socket exists..."
if [ -S "/run/liquidsoap/radio.sock" ]; then
    echo "  ✓ Unix socket exists"
else
    echo "  ✗ Unix socket NOT found"
    exit 1
fi

# Test 3: Test socket connection
echo "[Test 3] Test socket connection..."
if echo "help" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock > /dev/null 2>&1; then
    echo "  ✓ Socket connection successful"
else
    echo "  ✗ Socket connection failed"
    exit 1
fi

# Test 4: Verify queue sources are initialized
echo "[Test 4] Verify queue sources..."
QUEUES=$(echo "help" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock | grep -E "(override|music|breaks)" | wc -l)
if [ "$QUEUES" -ge 3 ]; then
    echo "  ✓ All queue sources detected (found $QUEUES)"
else
    echo "  ✗ Missing queue sources (found $QUEUES, expected ≥3)"
    exit 1
fi

# Test 5: Verify drops directory monitoring
echo "[Test 5] Verify drops directory..."
if [ -d "/srv/ai_radio/drops/processed" ]; then
    echo "  ✓ Drops directory structure exists"
else
    echo "  ✗ Drops directory structure missing"
    exit 1
fi

# Test 6: Verify watchdog service
echo "[Test 6] Verify watchdog service..."
if systemctl is-active --quiet ai-radio-watch-drops; then
    echo "  ✓ Watchdog service is running"
else
    echo "  ✗ Watchdog service is NOT running"
    exit 1
fi

# Test 7: Verify control directory
echo "[Test 7] Verify control directory..."
if [ -d "/srv/ai_radio/control" ]; then
    echo "  ✓ Control directory exists"
else
    echo "  ✗ Control directory missing"
    exit 1
fi

# Test 8: Test force break script
echo "[Test 8] Test force break script..."
if [ -x "/srv/ai_radio/scripts/force-break.sh" ]; then
    echo "  ✓ Force break script is executable"
else
    echo "  ✗ Force break script missing or not executable"
    exit 1
fi

# Test 9: Verify stream is broadcasting
echo "[Test 9] Verify stream is broadcasting..."
if curl -s -I http://127.0.0.1:8000/radio | grep -q "200 OK"; then
    echo "  ✓ Stream is broadcasting"
else
    echo "  ✗ Stream is NOT broadcasting"
    exit 1
fi

# Test 10: Verify fallback chain status
echo "[Test 10] Check fallback chain status..."
if echo "main_fallback.status" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock > /dev/null 2>&1; then
    echo "  ✓ Fallback chain is operational"
else
    echo "  ✗ Fallback chain query failed"
    exit 1
fi

echo
echo "=== All Phase 3 Tests Passed ✓ ==="
TESTEOF

scp /tmp/test-phase3.sh ubuntu@10.10.0.86:/tmp/test-phase3.sh
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/test-phase3.sh /srv/ai_radio/scripts/test-phase3.sh && sudo chmod +x /srv/ai_radio/scripts/test-phase3.sh"
```

Expected: Test script created and executable

**Step 2: Run Phase 3 tests**

Run:
```bash
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/test-phase3.sh"
```

Expected: All tests pass

---

## Task 10: Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE3_COMPLETE.md`

**Step 1: Create Phase 3 completion documentation**

Create file with operational guide and architecture notes:

```markdown
# Phase 3: Liquidsoap Advanced Configuration - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Multi-level fallback chain with queue management, operator controls, and zero dead-air guarantees is fully operational.

## Implemented Components

### Queue Management
- ✅ Operator override queue (highest priority) - request.queue(id="override")
- ✅ Music queue (main content) - request.queue(id="music")
- ✅ Break queue (news/weather) - request.queue(id="breaks")
- ✅ Filesystem drop-in monitoring (/srv/ai_radio/drops/)
- ✅ Unix socket interface for runtime control

### Control Interfaces
- ✅ Drop-in queue (copy MP3 → automatic play)
- ✅ Force break trigger (/srv/ai_radio/control/force_break)
- ✅ Unix socket commands (queue inspection, manual pushes)
- ✅ Python watchdog service with automatic file processing

### Fallback Chain
- ✅ 6-level fallback: override → forced breaks → music → beds → safety → emergency
- ✅ Track-sensitive transitions (waits for song endings)
- ✅ Zero dead-air guarantee
- ✅ Phase 1 sources integrated (safety_playlist, emergency_tone)

## Usage

### Drop a File for Immediate Play

```bash
# Copy MP3 to drops directory (from operator machine)
scp urgent-announcement.mp3 ubuntu@10.10.0.86:/srv/ai_radio/drops/

# File will be automatically pushed to override queue within seconds
# Check processed directory after playback
ssh ubuntu@10.10.0.86 "ls /srv/ai_radio/drops/processed/"
```

### Force an Immediate Break

```bash
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/force-break.sh"
```

### Queue Inspection via Socket

```bash
# Connect to Unix socket
ssh ubuntu@10.10.0.86 "socat - UNIX-CONNECT:/run/liquidsoap/radio.sock"

# Show override queue contents
override.queue

# Show music queue contents
music.queue

# Show break queue contents
breaks.queue

# Show current fallback source
main_fallback.status

# Exit
exit
```

### Manual Queue Push

```bash
# Add file to music queue
ssh ubuntu@10.10.0.86 "echo 'music.push /srv/ai_radio/assets/music/<sha256>.mp3' | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIQUIDSOAP FALLBACK CHAIN                 │
├─────────────────────────────────────────────────────────────┤
│ Level 1: Override Queue  ← Drop-in files (watchdog)         │
│ Level 2: Forced Breaks   ← Force break flag file            │
│ Level 3: Music Queue     ← Enqueue service (Phase 5)        │
│ Level 4: Beds            ← Short station IDs (kind='bed')   │
│ Level 5: Safety Playlist ← Fallback music (Phase 1)         │
│ Level 6: Emergency Tone  ← Loops forever (never fails)      │
├─────────────────────────────────────────────────────────────┤
│ → Normalize (-18 LUFS) → Icecast Output (192kbps MP3)      │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Files

- **Liquidsoap**: `/srv/ai_radio/config/radio.liq`
- **Watchdog Script**: `/srv/ai_radio/scripts/watch_drops.py`
- **Force Break**: `/srv/ai_radio/scripts/force-break.sh`
- **Unix Socket**: `/run/liquidsoap/radio.sock`

## Services

- **ai-radio-liquidsoap.service**: Main playout engine
- **ai-radio-watch-drops.service**: Drop-in file monitoring

## Directories

- `/srv/ai_radio/drops/`: Drop-in file input
- `/srv/ai_radio/drops/processed/`: Processed drop-ins
- `/srv/ai_radio/control/`: Control flag files
- `/srv/ai_radio/assets/beds/`: Short station ID audio

## Next Steps

**Phase 2 (Asset Management)** must be implemented BEFORE Phase 4:
- Music library ingestion with ffmpeg-normalize
- Metadata extraction (title, artist, album)
- SHA256 asset ID generation
- SQLite database population

After Phase 2, **Phase 4 (Content Generation)** will implement:
- LLM integration for bulletin scripting
- NWS API for weather data
- RSS aggregation for news
- TTS integration for voice synthesis
- Atomic file output to break queue

## SOW Compliance

✅ Section 3: Non-Negotiable #1 (Liquidsoap playout engine)
✅ Section 3: Non-Negotiable #2 (Producer/consumer separation via queues)
✅ Section 3: Non-Negotiable #4 (Evergreen fallback → safety_playlist)
✅ Section 6: Database schema alignment (kind='bed' for bumper-style content)
✅ Section 9: Multi-level fallback chain with queue sources
✅ Section 9: Track-sensitive transitions
✅ Section 10: Human override mechanisms (drop-in, force break, socket)
```

Write to VM:

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/docs"

cat > /tmp/PHASE3_COMPLETE.md << 'DOCEOF'
# Phase 3: Liquidsoap Advanced Configuration - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Multi-level fallback chain with queue management, operator controls, and zero dead-air guarantees is fully operational.

## Implemented Components

### Queue Management
- ✅ Operator override queue (highest priority) - request.queue(id="override")
- ✅ Music queue (main content) - request.queue(id="music")
- ✅ Break queue (news/weather) - request.queue(id="breaks")
- ✅ Filesystem drop-in monitoring (/srv/ai_radio/drops/)
- ✅ Unix socket interface for runtime control

### Control Interfaces
- ✅ Drop-in queue (copy MP3 → automatic play)
- ✅ Force break trigger (/srv/ai_radio/control/force_break)
- ✅ Unix socket commands (queue inspection, manual pushes)
- ✅ Python watchdog service with automatic file processing

### Fallback Chain
- ✅ 6-level fallback: override → forced breaks → music → beds → safety → emergency
- ✅ Track-sensitive transitions (waits for song endings)
- ✅ Zero dead-air guarantee
- ✅ Phase 1 sources integrated (safety_playlist, emergency_tone)

## Usage

### Drop a File for Immediate Play

```bash
# Copy MP3 to drops directory (from operator machine)
scp urgent-announcement.mp3 ubuntu@10.10.0.86:/srv/ai_radio/drops/

# File will be automatically pushed to override queue within seconds
# Check processed directory after playback
ssh ubuntu@10.10.0.86 "ls /srv/ai_radio/drops/processed/"
```

### Force an Immediate Break

```bash
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/force-break.sh"
```

### Queue Inspection via Socket

```bash
# Connect to Unix socket
ssh ubuntu@10.10.0.86 "socat - UNIX-CONNECT:/run/liquidsoap/radio.sock"

# Show override queue contents
override.queue

# Show music queue contents
music.queue

# Show break queue contents
breaks.queue

# Show current fallback source
main_fallback.status

# Exit
exit
```

### Manual Queue Push

```bash
# Add file to music queue
ssh ubuntu@10.10.0.86 "echo 'music.push /srv/ai_radio/assets/music/<sha256>.mp3' | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIQUIDSOAP FALLBACK CHAIN                 │
├─────────────────────────────────────────────────────────────┤
│ Level 1: Override Queue  ← Drop-in files (watchdog)         │
│ Level 2: Forced Breaks   ← Force break flag file            │
│ Level 3: Music Queue     ← Enqueue service (Phase 5)        │
│ Level 4: Beds            ← Short station IDs (kind='bed')   │
│ Level 5: Safety Playlist ← Fallback music (Phase 1)         │
│ Level 6: Emergency Tone  ← Loops forever (never fails)      │
├─────────────────────────────────────────────────────────────┤
│ → Normalize (-18 LUFS) → Icecast Output (192kbps MP3)      │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Files

- **Liquidsoap**: `/srv/ai_radio/config/radio.liq`
- **Watchdog Script**: `/srv/ai_radio/scripts/watch_drops.py`
- **Force Break**: `/srv/ai_radio/scripts/force-break.sh`
- **Unix Socket**: `/run/liquidsoap/radio.sock`

## Services

- **ai-radio-liquidsoap.service**: Main playout engine
- **ai-radio-watch-drops.service**: Drop-in file monitoring

## Directories

- `/srv/ai_radio/drops/`: Drop-in file input
- `/srv/ai_radio/drops/processed/`: Processed drop-ins
- `/srv/ai_radio/control/`: Control flag files
- `/srv/ai_radio/assets/beds/`: Short station ID audio

## Next Steps

**Phase 2 (Asset Management)** must be implemented BEFORE Phase 4:
- Music library ingestion with ffmpeg-normalize
- Metadata extraction (title, artist, album)
- SHA256 asset ID generation
- SQLite database population

After Phase 2, **Phase 4 (Content Generation)** will implement:
- LLM integration for bulletin scripting
- NWS API for weather data
- RSS aggregation for news
- TTS integration for voice synthesis
- Atomic file output to break queue

## SOW Compliance

✅ Section 3: Non-Negotiable #1 (Liquidsoap playout engine)
✅ Section 3: Non-Negotiable #2 (Producer/consumer separation via queues)
✅ Section 3: Non-Negotiable #4 (Evergreen fallback → safety_playlist)
✅ Section 6: Database schema alignment (kind='bed' for bumper-style content)
✅ Section 9: Multi-level fallback chain with queue sources
✅ Section 9: Track-sensitive transitions
✅ Section 10: Human override mechanisms (drop-in, force break, socket)
DOCEOF

scp /tmp/PHASE3_COMPLETE.md ubuntu@10.10.0.86:/tmp/PHASE3_COMPLETE.md
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/PHASE3_COMPLETE.md /srv/ai_radio/docs/PHASE3_COMPLETE.md"
```

Expected: Documentation created

---

## Key Adaptations from Original Plan

1. **Configuration Path**: Changed all references from `/srv/ai_radio/radio.liq` to `/srv/ai_radio/config/radio.liq`
2. **Mount Point**: Changed from `/stream` to `/radio` (matches Phase 1)
3. **Bumpers → Beds**: Renamed "bumpers" to "beds" to align with database schema (kind='bed')
4. **Safety Playlist**: Used existing `safety_playlist` name from Phase 1 (not "evergreen")
5. **OPAM Wrapper**: Used `/srv/ai_radio/scripts/liquidsoap-wrapper.sh` for liquidsoap commands
6. **Python Environment**: Used `uv run` for watchdog service (matches Phase 1 uv setup)
7. **Break Freshness**: Removed inline Liquidsoap break freshness checking (will be producer responsibility in Phase 4)
8. **MP3 Encoding**: Verified compatibility (Phase 1 already uses MP3) ✓

---

## Definition of Done

- [ ] Pre-flight verification complete (config paths, OPAM wrapper)
- [ ] Python watchdog dependency installed
- [ ] Queue sources defined (override, music, breaks)
- [ ] Unix socket configuration added (if missing)
- [ ] Filesystem drop-in monitoring configured
- [ ] Force break trigger working
- [ ] Multi-level fallback chain (6 levels) operational
- [ ] Configuration validation passing
- [ ] Liquidsoap restart successful
- [ ] Watchdog service running
- [ ] Integration tests passing
- [ ] Documentation complete

## Verification Commands

```bash
# 1. Validate Liquidsoap configuration
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/liquidsoap-wrapper.sh --check /srv/ai_radio/config/radio.liq"

# 2. Verify services running
ssh ubuntu@10.10.0.86 "sudo systemctl status ai-radio-liquidsoap.service ai-radio-watch-drops.service"

# 3. Test socket connection
ssh ubuntu@10.10.0.86 "echo 'help' | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock | head -20"

# 4. Run integration tests
ssh ubuntu@10.10.0.86 "/srv/ai_radio/scripts/test-phase3.sh"

# 5. Verify stream is broadcasting
curl -I https://radio.clintecker.com/radio
```

All commands should complete successfully without errors.

---

## Execution Order

**Phase 3 must be executed AFTER Phase 1 and BEFORE Phase 2** for clean dependency flow:
- Phase 1 establishes base Liquidsoap + MP3 encoding ✅ COMPLETE
- **Phase 3 adds queue infrastructure** ← Execute this plan
- Phase 2 populates music library (will use Phase 3 queues)
- Phase 4 generates breaks (will use Phase 3 break queue)
- Phase 5 schedules content (will use Phase 3 queue interfaces)

---

## Ready to Execute

This adapted plan accounts for Phase 1 implementation reality and can be executed safely.

Use: `superpowers:executing-plans` to implement task-by-task with review checkpoints.
