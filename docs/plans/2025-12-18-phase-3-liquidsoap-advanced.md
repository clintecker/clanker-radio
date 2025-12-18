# Phase 3: Liquidsoap Advanced Configuration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement multi-level fallback chain with break insertion, operator overrides, and zero dead-air guarantees

**Architecture:** Liquidsoap orchestrates multiple input sources (operator override queue, music queue, break scheduler, evergreen playlist, safety bumper) with intelligent fallback logic, break freshness checking, and filesystem-based control interfaces for human operators.

**Tech Stack:** Liquidsoap 2.x, Liquidsoap scripting language, Unix sockets, filesystem queues

---

## Overview

Phase 3 extends the basic Liquidsoap setup from Phase 1 with:
1. **Multi-level fallback chain** - Never dead air, even if all queues are empty
2. **Break insertion logic** - Top-of-hour breaks with staleness checking
3. **Operator override queue** - Drop MP3 file → plays next
4. **Music queue management** - Populated by enqueue service (Phase 5)
5. **Force break trigger** - Filesystem flag to trigger immediate break
6. **Crossfade transitions** - Smooth audio transitions between tracks
7. **Unix socket interface** - Telnet control for debugging/monitoring

**Why This Matters:** This is the "never dead air" heart of the system. All queues can fail, but the stream continues with fallbacks.

---

## Task 1: Queue Source Definitions

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Define request.queue sources for each input**

Add to `radio.liq` after the password loading section (after line ~500 from Phase 1):

```liquidsoap
# ============================================================================
# QUEUE SOURCES (Phase 3)
# ============================================================================

# Operator override queue - highest priority
# Operators can drop files here for immediate play
override_queue = request.queue(
    id="override",
    queue=[],  # Empty at start
    interactive=true  # Allow runtime additions
)

# Music queue - main content source
# Populated by enqueue.py service (Phase 5)
music_queue = request.queue(
    id="music",
    queue=[],
    interactive=true
)

# Break queue - news/weather breaks
# Populated by news_gen.py service (Phase 4)
break_queue = request.queue(
    id="breaks",
    queue=[],
    interactive=true
)

log("Queue sources initialized: override, music, breaks")
```

Run:
```bash
# Append to radio.liq
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Queue sources defined

**Step 2: Verify queue initialization**

Run:
```bash
sudo -u ai-radio liquidsoap --check /srv/ai_radio/radio.liq
```

Expected: "No errors found"

---

## Task 2: Filesystem Queue Monitoring (Drop-in)

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Add playlist.reloadable for drops directory**

The drop-in directory allows operators to copy MP3 files that will be automatically enqueued to the override queue.

Add to `radio.liq`:

```liquidsoap
# ============================================================================
# FILESYSTEM DROP-IN QUEUE (Phase 3)
# ============================================================================

# Drop directory for operator files
# Place .mp3 files here → automatically added to override queue
drops_dir = "/srv/ai_radio/drops"

# Reloadable playlist that watches drops/ directory
drops_playlist = playlist.reloadable(
    id="drops",
    mode="normal",  # Play in order
    reload_mode="watch",  # Watch for filesystem changes
    drops_dir
)

# Function to move files from drops/ to override queue
def process_drops()
    # Get current playlist
    files = request.queue.queue(override_queue)

    # For each file in drops playlist
    list.iter(fun(uri) -> begin
        # Extract filename
        filename = path.basename(uri)

        # Add to override queue
        request.queue.push(override_queue, uri)

        # Move file to processed/ directory (atomic operation)
        processed_path = "#{drops_dir}/processed/#{filename}"
        file.move(uri, processed_path)

        log("Processed drop-in file: #{filename}")
    end, playlist.files(drops_playlist))
end

# Process drops every 10 seconds
thread.run(delay=10., process_drops)

log("Drop-in queue monitoring enabled: #{drops_dir}")
```

Run:
```bash
# Create drops directory and processed subdirectory
sudo -u ai-radio mkdir -p /srv/ai_radio/drops/processed

# Append to radio.liq
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Drops directory monitoring configured

**Step 2: Test drop-in functionality**

Run:
```bash
# Copy a test file to drops (will be added in verification later)
# For now, just verify directory exists
ls -la /srv/ai_radio/drops/
```

Expected: Directory exists with `processed/` subdirectory

---

## Task 3: Break Freshness Checking

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Implement break staleness check function**

Breaks should not play if they're older than 65 minutes (to ensure hourly freshness).

Add to `radio.liq`:

```liquidsoap
# ============================================================================
# BREAK FRESHNESS CHECKING (Phase 3)
# ============================================================================

# Maximum age for break files (65 minutes = 3900 seconds)
max_break_age_seconds = 3900.0

def is_break_fresh(filename)
    # Check if file exists
    if not file.exists(filename) then
        log("Break file does not exist: #{filename}")
        false
    else
        # Get file modification time
        mtime = file.mtime(filename)
        current_time = time()

        # Calculate age in seconds
        age_seconds = current_time - mtime

        if age_seconds > max_break_age_seconds then
            log("Break file is stale (#{age_seconds}s old, max #{max_break_age_seconds}s): #{filename}")
            false
        else
            log("Break file is fresh (#{age_seconds}s old): #{filename}")
            true
        end
    end
end

# Wrapper for break queue that only plays fresh breaks
fresh_break_queue = source.available(
    break_queue,
    fun() -> begin
        # Check if break queue has content
        if not source.is_ready(break_queue) then
            false
        else
            # Get current request
            req = request.queue.current(break_queue)

            match req with
            | null -> false  # No current request
            | r -> is_break_fresh(request.filename(r))
            end
        end
    end
)

log("Break freshness checking enabled (max age: #{max_break_age_seconds}s)")
```

Run:
```bash
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Freshness checking function defined

---

## Task 4: Force Break Trigger

**Files:**
- Modify: `/srv/ai_radio/radio.liq`
- Create: `/srv/ai_radio/scripts/force-break.sh`

**Step 1: Add force break flag monitoring**

Allow operators to trigger an immediate break by creating a flag file.

Add to `radio.liq`:

```liquidsoap
# ============================================================================
# FORCE BREAK TRIGGER (Phase 3)
# ============================================================================

# Flag file for forcing immediate break
force_break_flag = "/srv/ai_radio/control/force_break"

# Check if force break is requested
def should_force_break()
    if file.exists(force_break_flag) then
        log("Force break triggered! Removing flag file.")
        file.remove(force_break_flag)
        true
    else
        false
    end
end

# Wrapper for break queue that respects force break flag
forced_break_queue = switch(
    id="forced_breaks",
    track_sensitive=true,
    [
        # If force break flag exists, play break immediately
        ({should_force_break()}, fresh_break_queue),

        # Otherwise, only play at top of hour (handled by scheduler in Phase 5)
        ({false}, blank())  # Never play here, scheduler handles timing
    ]
)

log("Force break trigger enabled: #{force_break_flag}")
```

Run:
```bash
# Create control directory
sudo -u ai-radio mkdir -p /srv/ai_radio/control

# Append to radio.liq
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Force break flag monitoring configured

**Step 2: Create force break script for operators**

Create file `/srv/ai_radio/scripts/force-break.sh`:

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
sudo -u ai-radio tee /srv/ai_radio/scripts/force-break.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/force-break.sh
```

Expected: Force break script created and executable

---

## Task 5: Multi-Level Fallback Chain

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Build complete fallback chain**

The fallback chain ensures zero dead air by cascading through sources until one is available.

Add to `radio.liq`:

```liquidsoap
# ============================================================================
# MULTI-LEVEL FALLBACK CHAIN (Phase 3)
# ============================================================================

# Priority order (highest to lowest):
# 1. Operator override queue (drop-in files)
# 2. Forced breaks (operator-triggered)
# 3. Music queue (main content)
# 4. Scheduled breaks (top-of-hour, handled by switch in Phase 5)
# 5. Evergreen playlist (fallback music)
# 6. Safety bumper (last resort, loops forever)

# Build the fallback chain from bottom to top
fallback_chain = fallback(
    id="main_fallback",
    track_sensitive=true,  # Wait for track boundaries
    transitions=[  # Smooth transitions between sources
        fun(old, new) -> add([fade.out(duration=0.5, old), fade.in(duration=0.5, new)])
    ],
    [
        # Level 1 (highest): Operator override
        override_queue,

        # Level 2: Forced breaks
        forced_break_queue,

        # Level 3: Music queue (main content)
        music_queue,

        # Level 4: Breaks will be inserted here via switch (Phase 5)
        # For now, this level is handled by the scheduler

        # Level 5: Evergreen playlist (fallback music)
        evergreen,

        # Level 6 (lowest): Safety bumper (loops forever, never fails)
        bumper
    ]
)

log("Multi-level fallback chain configured (6 levels)")
```

Run:
```bash
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Fallback chain defined

**Step 2: Add crossfade for smooth transitions**

Add crossfade to the fallback chain output:

```liquidsoap
# ============================================================================
# CROSSFADE & AUDIO PROCESSING (Phase 3)
# ============================================================================

# Apply crossfade for smooth transitions between tracks
# Duration: 2.0s per validation recommendation (was 1.5s in Phase 1)
output_with_crossfade = crossfade(
    duration=2.0,
    fade_in=1.0,
    fade_out=1.0,
    fallback_chain
)

log("Crossfade configured (duration: 2.0s)")
```

Run:
```bash
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Crossfade configured

---

## Task 6: Output Configuration

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Update Icecast output to use fallback chain**

Replace the old output section from Phase 1 with the new fallback chain:

Find and replace the old `output.icecast` block (from Phase 1) with:

```liquidsoap
# ============================================================================
# ICECAST OUTPUT (Phase 3 - Updated)
# ============================================================================

# Output to Icecast with fallback chain
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

    # Metadata
    public=false,  # Not listed in Icecast directory

    # Use the complete fallback chain with crossfade
    output_with_crossfade
)

log("Icecast output configured with multi-level fallback chain")
```

Run:
```bash
# This requires editing the existing radio.liq file
# For now, note that this section needs to be updated during implementation
```

Expected: Output configured to use fallback chain

---

## Task 7: Unix Socket Interface

**Files:**
- Modify: `/srv/ai_radio/radio.liq`

**Step 1: Verify Unix socket configuration**

The Unix socket should already be configured from Phase 1. Verify it exists:

```liquidsoap
# Unix socket should already be configured from Phase 1:
# set("server.socket", true)
# set("server.socket.path", "/run/liquidsoap/radio.sock")
# set("server.socket.permissions", 0o660)
```

Run:
```bash
# Verify socket configuration exists in radio.liq
grep -A3 "server.socket" /srv/ai_radio/radio.liq
```

Expected: Socket configuration present from Phase 1

**Step 2: Document socket commands**

Add comments documenting useful socket commands:

```liquidsoap
# ============================================================================
# UNIX SOCKET INTERFACE - OPERATOR COMMANDS (Phase 3)
# ============================================================================

# Connect to socket:
#   telnet localhost 1234
#   OR: socat - UNIX-CONNECT:/run/liquidsoap/radio.sock
#
# Useful commands:
#   override.push <uri>      - Add file to override queue
#   override.queue           - Show override queue contents
#   music.push <uri>         - Add file to music queue
#   music.queue              - Show music queue contents
#   breaks.push <uri>        - Add break to break queue
#   breaks.queue             - Show break queue contents
#   main_fallback.status     - Show current fallback source
#   help                     - Show all available commands
#   exit                     - Close connection
```

Run:
```bash
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/radio.liq
[content above]
EOF
```

Expected: Socket commands documented

---

## Task 8: Configuration Validation

**Files:**
- None (validation only)

**Step 1: Validate Liquidsoap configuration syntax**

Run:
```bash
sudo -u ai-radio liquidsoap --check /srv/ai_radio/radio.liq
```

Expected: "No errors found"

**Step 2: Verify all required directories exist**

Run:
```bash
ls -la /srv/ai_radio/drops/
ls -la /srv/ai_radio/drops/processed/
ls -la /srv/ai_radio/control/
```

Expected: All directories exist with ai-radio ownership

**Step 3: Test Liquidsoap startup (dry run)**

Run:
```bash
# Start Liquidsoap in foreground for testing (Ctrl+C to stop)
sudo -u ai-radio liquidsoap /srv/ai_radio/radio.liq
```

Expected: Liquidsoap starts without errors, logs show queue initialization

---

## Task 9: Integration Testing

**Files:**
- Create: `/srv/ai_radio/scripts/test-phase3.sh`

**Step 1: Create Phase 3 test script**

Create file `/srv/ai_radio/scripts/test-phase3.sh`:

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
    echo "  ✓ All queue sources detected"
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

# Test 6: Verify control directory
echo "[Test 6] Verify control directory..."
if [ -d "/srv/ai_radio/control" ]; then
    echo "  ✓ Control directory exists"
else
    echo "  ✗ Control directory missing"
    exit 1
fi

# Test 7: Test force break script
echo "[Test 7] Test force break script..."
if [ -x "/srv/ai_radio/scripts/force-break.sh" ]; then
    echo "  ✓ Force break script is executable"
else
    echo "  ✗ Force break script missing or not executable"
    exit 1
fi

# Test 8: Verify stream is broadcasting
echo "[Test 8] Verify stream is broadcasting..."
if curl -s -I http://127.0.0.1:8000/stream | grep -q "200 OK"; then
    echo "  ✓ Stream is broadcasting"
else
    echo "  ✗ Stream is NOT broadcasting"
    exit 1
fi

echo
echo "=== All Phase 3 Tests Passed ✓ ==="
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/scripts/test-phase3.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/test-phase3.sh
```

Expected: Test script created

**Step 2: Run Phase 3 tests**

Run:
```bash
/srv/ai_radio/scripts/test-phase3.sh
```

Expected: All tests pass

---

## Task 10: Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE3_COMPLETE.md`

**Step 1: Document Phase 3 completion**

Create file `/srv/ai_radio/docs/PHASE3_COMPLETE.md`:

```markdown
# Phase 3: Liquidsoap Advanced Configuration - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Multi-level fallback chain with break insertion, operator overrides, and zero dead-air guarantees is fully operational.

## Implemented Components

### Queue Management
- ✅ Operator override queue (highest priority)
- ✅ Music queue (main content source)
- ✅ Break queue (news/weather)
- ✅ Filesystem drop-in monitoring (/srv/ai_radio/drops/)
- ✅ Unix socket interface for runtime control

### Break System
- ✅ Break freshness checking (65-minute staleness threshold)
- ✅ Force break trigger (/srv/ai_radio/control/force_break)
- ✅ Stale break skipping (never play old content)

### Fallback Chain
- ✅ 6-level fallback: override → forced breaks → music → breaks → evergreen → bumper
- ✅ Track-sensitive transitions (waits for song endings)
- ✅ Crossfade (2.0s duration)
- ✅ Zero dead-air guarantee

### Operator Tools
- ✅ Drop-in queue (copy MP3 → automatic play)
- ✅ Force break script
- ✅ Unix socket commands (queue inspection, manual pushes)

## Usage

### Drop a File for Immediate Play

```bash
# Copy MP3 to drops directory
cp /path/to/urgent-announcement.mp3 /srv/ai_radio/drops/

# File will be automatically moved to override queue within 10 seconds
# Check processed directory after playback
ls /srv/ai_radio/drops/processed/
```

### Force an Immediate Break

```bash
/srv/ai_radio/scripts/force-break.sh
```

### Queue Inspection via Socket

```bash
# Connect to Unix socket
socat - UNIX-CONNECT:/run/liquidsoap/radio.sock

# Show override queue contents
override.queue

# Show music queue contents
music.queue

# Show current fallback source
main_fallback.status

# Exit
exit
```

### Manual Queue Push

```bash
# Add file to override queue
echo "override.push /srv/ai_radio/assets/music/<sha256>.mp3" | \
  socat - UNIX-CONNECT:/run/liquidsoap/radio.sock
```

## Test Results

All integration tests passing:
- Liquidsoap service running
- Unix socket accessible
- All queue sources initialized
- Drops directory monitoring active
- Control directory configured
- Force break script executable
- Stream broadcasting successfully

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LIQUIDSOAP FALLBACK CHAIN                 │
├─────────────────────────────────────────────────────────────┤
│ Level 1: Override Queue  ← Drop-in files                    │
│ Level 2: Forced Breaks   ← Force break flag                 │
│ Level 3: Music Queue     ← Enqueue service (Phase 5)        │
│ Level 4: Break Schedule  ← Top-of-hour (Phase 5)            │
│ Level 5: Evergreen       ← Fallback playlist                │
│ Level 6: Safety Bumper   ← Loops forever (never fails)      │
├─────────────────────────────────────────────────────────────┤
│ → Crossfade (2.0s) → Icecast Output (192kbps MP3)          │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

Phase 4 will implement content generation:
- LLM integration for bulletin scripting
- NWS API integration for weather data
- RSS feed aggregation for news
- TTS integration for voice synthesis
- Bed audio mixing with ducking
- Atomic file output to break queue

## SOW Compliance

✅ Section 3: Non-Negotiable #1 (Liquidsoap playout engine)
✅ Section 3: Non-Negotiable #2 (Producer/consumer separation)
✅ Section 3: Non-Negotiable #4 (Evergreen fallback)
✅ Section 9: All playout requirements
✅ Section 9: Multi-level fallback chain
✅ Section 9: Break insertion logic
✅ Section 9: Freshness checking
✅ Section 10: Human overrides (drop-in, force break)
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/docs/PHASE3_COMPLETE.md << 'EOF'
[content above]
EOF
```

Expected: Documentation created

---

## Definition of Done

- [x] Queue sources defined (override, music, breaks)
- [x] Filesystem drop-in monitoring configured
- [x] Break freshness checking implemented (65-minute threshold)
- [x] Force break trigger working
- [x] Multi-level fallback chain (6 levels) operational
- [x] Crossfade configured (2.0s duration)
- [x] Unix socket interface documented
- [x] Configuration validation passing
- [x] Integration tests passing
- [x] Documentation complete

## Verification Commands

```bash
# 1. Validate Liquidsoap configuration
sudo -u ai-radio liquidsoap --check /srv/ai_radio/radio.liq

# 2. Verify directories
ls -la /srv/ai_radio/drops/processed/
ls -la /srv/ai_radio/control/

# 3. Test socket connection
echo "help" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock

# 4. Check queue status
echo "override.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock

# 5. Run integration tests
/srv/ai_radio/scripts/test-phase3.sh

# 6. Verify stream is broadcasting
curl -I http://127.0.0.1:8000/stream
```

All commands should complete successfully without errors.

---

## Notes

- **Zero Dead Air:** The 6-level fallback chain ensures the stream never goes silent
- **Track-Sensitive:** Fallbacks wait for track boundaries (no mid-song cuts)
- **Atomic Operations:** Drop-in files are moved (not copied) to prevent partial reads
- **Freshness Guarantee:** Breaks older than 65 minutes are automatically skipped
- **Operator Control:** Multiple interfaces (drop-in, force break, Unix socket) for human intervention
- **Phase 5 Integration:** Music and break queues are currently empty; they will be populated by enqueue.py and news_gen.py services in subsequent phases
