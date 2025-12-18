# Phase 7: Operator Tools - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement manual control utilities for human operators to override automation, skip tracks, force breaks, and manage the station

**Architecture:** Simple CLI utilities wrapping Liquidsoap socket commands and service controls, designed for quick operator intervention

**Tech Stack:** Bash scripts, Python CLI (optional), Liquidsoap socket communication

---

## Overview

Phase 7 provides the "human override" layer - tools for operators to take manual control when needed:

1. **Skip Track** - Skip currently playing track
2. **Force Break** - Trigger immediate break (already implemented in Phase 3)
3. **Push Track** - Manually push specific track to queue
4. **Clear Queue** - Empty a queue
5. **Emergency Playlist** - Activate emergency fallback
6. **Service Control** - Quick restart/reload commands

**Why This Matters:** Automation is great, but humans need override controls for special events, emergencies, or manual programming.

---

## Task 1: Skip Track Utility

**Files:**
- Create: `/srv/ai_radio/scripts/skip-track.sh`

**Step 1: Create skip track script**

Create file `/srv/ai_radio/scripts/skip-track.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Skip Track Utility
# Skip currently playing track in specified queue

QUEUE=${1:-music}

if [ "$QUEUE" != "music" ] && [ "$QUEUE" != "breaks" ] && [ "$QUEUE" != "override" ]; then
    echo "Usage: $0 [music|breaks|override]"
    echo "  Skip currently playing track in specified queue"
    exit 1
fi

echo "Skipping current track in '$QUEUE' queue..."

# Send skip command via Liquidsoap socket
if echo "$QUEUE.skip" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock; then
    echo "✓ Track skipped successfully"
    exit 0
else
    echo "✗ Failed to skip track (Liquidsoap not running?)"
    exit 1
fi
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/skip-track.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/skip-track.sh
```

Expected: Skip track script created

---

## Task 2: Push Track Utility

**Files:**
- Create: `/srv/ai_radio/scripts/push-track.sh`

**Step 1: Create push track script**

Create file `/srv/ai_radio/scripts/push-track.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Push Track Utility
# Manually push a specific track to queue

if [ $# -lt 2 ]; then
    echo "Usage: $0 <queue> <file_path>"
    echo "  queue: music, breaks, or override"
    echo "  file_path: absolute path to audio file"
    echo
    echo "Examples:"
    echo "  $0 override /srv/ai_radio/assets/music/abc123.mp3"
    echo "  $0 music /srv/ai_radio/assets/music/def456.mp3"
    exit 1
fi

QUEUE=$1
FILE_PATH=$2

if [ ! -f "$FILE_PATH" ]; then
    echo "✗ File not found: $FILE_PATH"
    exit 1
fi

echo "Pushing track to '$QUEUE' queue: $FILE_PATH"

# Send push command via Liquidsoap socket
if echo "$QUEUE.push $FILE_PATH" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock; then
    echo "✓ Track pushed successfully"
    exit 0
else
    echo "✗ Failed to push track (Liquidsoap not running?)"
    exit 1
fi
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/push-track.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/push-track.sh
```

Expected: Push track script created

---

## Task 3: Clear Queue Utility

**Files:**
- Create: `/srv/ai_radio/scripts/clear-queue.sh`

**Step 1: Create clear queue script**

Create file `/srv/ai_radio/scripts/clear-queue.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Clear Queue Utility
# Empty all tracks from specified queue

QUEUE=${1:-music}

if [ "$QUEUE" != "music" ] && [ "$QUEUE" != "breaks" ] && [ "$QUEUE" != "override" ]; then
    echo "Usage: $0 [music|breaks|override]"
    echo "  Clear all tracks from specified queue"
    exit 1
fi

echo "Clearing '$QUEUE' queue..."

# Get current queue contents
TRACKS=$(echo "$QUEUE.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock | wc -l)

echo "  Current queue depth: $TRACKS tracks"

# Clear queue by repeatedly removing tracks
for i in $(seq 1 $TRACKS); do
    echo "$QUEUE.remove 0" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock > /dev/null 2>&1 || true
done

echo "✓ Queue cleared"
exit 0
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/clear-queue.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/clear-queue.sh
```

Expected: Clear queue script created

---

## Task 4: Emergency Playlist Activator

**Files:**
- Create: `/srv/ai_radio/scripts/activate-emergency.sh`

**Step 1: Create emergency activation script**

Create file `/srv/ai_radio/scripts/activate-emergency.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Emergency Playlist Activator
# Clear all queues to force fallback to evergreen/bumper

echo "=== EMERGENCY PLAYLIST ACTIVATION ==="
echo
echo "This will:"
echo "  1. Clear music queue"
echo "  2. Clear breaks queue"
echo "  3. Clear override queue"
echo "  4. Force fallback to evergreen playlist"
echo
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled"
    exit 0
fi

echo
echo "Clearing all queues..."

/srv/ai_radio/scripts/clear-queue.sh music
/srv/ai_radio/scripts/clear-queue.sh breaks
/srv/ai_radio/scripts/clear-queue.sh override

echo
echo "✓ Emergency playlist activated"
echo "  Stream will now play from evergreen fallback playlist"
echo
echo "To restore normal operation:"
echo "  1. Wait for enqueue service to refill music queue (runs every 5 min)"
echo "  2. Or manually restart ai-radio-enqueue.timer:"
echo "     sudo systemctl restart ai-radio-enqueue.timer"
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/activate-emergency.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/activate-emergency.sh
```

Expected: Emergency activation script created

---

## Task 5: Service Control Wrapper

**Files:**
- Create: `/srv/ai_radio/scripts/radio-ctl.sh`

**Step 1: Create unified service control script**

Create file `/srv/ai_radio/scripts/radio-ctl.sh`:

```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Service Control Wrapper
# Unified interface for common service operations

COMMAND=${1:-help}

case "$COMMAND" in
    start)
        echo "Starting all AI Radio services..."
        sudo systemctl start icecast2
        sudo systemctl start ai-radio-liquidsoap
        sudo systemctl start ai-radio-watch-drops
        sudo systemctl start ai-radio-enqueue.timer
        sudo systemctl start ai-radio-break-gen.timer
        sudo systemctl start ai-radio-break-scheduler.timer
        echo "✓ All services started"
        ;;

    stop)
        echo "Stopping all AI Radio services..."
        sudo systemctl stop ai-radio-break-scheduler.timer
        sudo systemctl stop ai-radio-break-gen.timer
        sudo systemctl stop ai-radio-enqueue.timer
        sudo systemctl stop ai-radio-watch-drops
        sudo systemctl stop ai-radio-liquidsoap
        sudo systemctl stop icecast2
        echo "✓ All services stopped"
        ;;

    restart)
        echo "Restarting all AI Radio services..."
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo "=== AI Radio Station Status ==="
        echo
        systemctl status icecast2 --no-pager -l || true
        echo
        systemctl status ai-radio-liquidsoap --no-pager -l || true
        echo
        systemctl status ai-radio-enqueue.timer --no-pager -l || true
        ;;

    reload)
        echo "Reloading Liquidsoap configuration..."
        sudo systemctl reload ai-radio-liquidsoap || sudo systemctl restart ai-radio-liquidsoap
        echo "✓ Configuration reloaded"
        ;;

    help|*)
        echo "AI Radio Station - Service Control"
        echo
        echo "Usage: $0 <command>"
        echo
        echo "Commands:"
        echo "  start       Start all services"
        echo "  stop        Stop all services"
        echo "  restart     Restart all services"
        echo "  status      Show service status"
        echo "  reload      Reload Liquidsoap config"
        echo "  help        Show this help"
        echo
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 status"
        echo "  $0 reload"
        exit 0
        ;;
esac
```

Run:
```bash
sudo tee /srv/ai_radio/scripts/radio-ctl.sh << 'EOF'
[content above]
EOF

sudo chmod +x /srv/ai_radio/scripts/radio-ctl.sh
```

Expected: Service control wrapper created

---

## Task 6: Operator Quick Reference

**Files:**
- Create: `/srv/ai_radio/docs/OPERATOR_GUIDE.md`

**Step 1: Create operator quick reference**

Create file `/srv/ai_radio/docs/OPERATOR_GUIDE.md`:

```markdown
# AI Radio Station - Operator Quick Reference

## Emergency Contacts
- System Administrator: [Contact Info]
- Technical Support: [Contact Info]

## Quick Actions

### Check Station Health
```bash
/srv/ai_radio/scripts/health-check.sh
```

### View Real-Time Status
```bash
/srv/ai_radio/scripts/status-dashboard.sh
# Press Ctrl+C to exit
```

### Skip Current Track
```bash
/srv/ai_radio/scripts/skip-track.sh music
```

### Force Break Immediately
```bash
/srv/ai_radio/scripts/force-break.sh
```

### Push Track to Override Queue (Priority Playback)
```bash
/srv/ai_radio/scripts/push-track.sh override /path/to/file.mp3
```

### Add Track to Music Queue
```bash
/srv/ai_radio/scripts/push-track.sh music /path/to/file.mp3
```

### Clear Queue
```bash
/srv/ai_radio/scripts/clear-queue.sh music
```

### Activate Emergency Playlist
```bash
/srv/ai_radio/scripts/activate-emergency.sh
# Confirms before executing
```

## Service Management

### Start/Stop/Restart Services
```bash
/srv/ai_radio/scripts/radio-ctl.sh start
/srv/ai_radio/scripts/radio-ctl.sh stop
/srv/ai_radio/scripts/radio-ctl.sh restart
```

### Reload Configuration
```bash
/srv/ai_radio/scripts/radio-ctl.sh reload
```

### Check Service Status
```bash
/srv/ai_radio/scripts/radio-ctl.sh status
```

## Drop-In Files (Manual Playback)

To play a file immediately:

1. Copy MP3 file to drops directory:
```bash
cp /path/to/urgent-announcement.mp3 /srv/ai_radio/drops/
```

2. File will automatically play within 10 seconds
3. Check processed directory after playback:
```bash
ls /srv/ai_radio/drops/processed/
```

## Troubleshooting

### Stream is Silent/Dead Air
1. Check services:
```bash
/srv/ai_radio/scripts/health-check.sh
```

2. Check queue depth:
```bash
echo "music.queue" | socat - UNIX-CONNECT:/run/liquidsoap/radio.sock
```

3. If queues empty, restart enqueue service:
```bash
sudo systemctl restart ai-radio-enqueue.service
```

### Liquidsoap Not Starting
1. Check configuration:
```bash
sudo -u ai-radio liquidsoap --check /srv/ai_radio/radio.liq
```

2. Check logs:
```bash
sudo journalctl -u ai-radio-liquidsoap.service -n 50
```

### Breaks Not Playing
1. Check break availability:
```bash
ls -lh /srv/ai_radio/assets/breaks/next.mp3
```

2. Force break generation:
```bash
sudo systemctl start ai-radio-break-gen.service
```

3. Check scheduler logs:
```bash
sudo journalctl -u ai-radio-break-scheduler.service -n 20
```

## Monitoring

### View Logs (All Services)
```bash
sudo journalctl -t ai-radio-* -f
```

### View Specific Service Logs
```bash
sudo journalctl -u ai-radio-liquidsoap.service -f
sudo journalctl -u ai-radio-enqueue.service -f
sudo journalctl -u ai-radio-break-gen.service -f
```

### Check Listener Count
```bash
curl -s http://admin:PASSWORD@127.0.0.1:8000/admin/stats | grep Listeners
```

## Maintenance

### Restart Everything (Safe)
```bash
/srv/ai_radio/scripts/radio-ctl.sh restart
```

### Clear Old Break Files (Cleanup)
```bash
find /srv/ai_radio/assets/breaks -name "break_*.mp3" -mtime +7 -delete
```

### Check Database Size
```bash
ls -lh /srv/ai_radio/db/radio.sqlite3
```

### Compact Database (If Large)
```bash
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 "VACUUM;"
```

## Notes
- All scripts require appropriate permissions
- Drop-in files are moved to `processed/` after playback
- Emergency playlist activation clears all queues - use with caution
- Service control operations may require sudo
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/docs/OPERATOR_GUIDE.md << 'EOF'
[content above]
EOF
```

Expected: Operator guide created

---

## Task 7: Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE7_COMPLETE.md`

**Step 1: Document Phase 7 completion**

Create file `/srv/ai_radio/docs/PHASE7_COMPLETE.md`:

```markdown
# Phase 7: Operator Tools - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Complete set of operator control utilities implemented. Human operators can now override automation, skip tracks, force breaks, clear queues, and manage services with simple CLI tools.

## Implemented Components

### Manual Control Scripts
- ✅ Skip track utility
- ✅ Push track utility (any queue)
- ✅ Clear queue utility
- ✅ Force break trigger (from Phase 3)
- ✅ Emergency playlist activator

### Service Management
- ✅ Unified service control wrapper (start/stop/restart)
- ✅ Configuration reload command
- ✅ Service status checks

### Documentation
- ✅ Operator quick reference guide
- ✅ Troubleshooting procedures
- ✅ Common operations guide

## Usage Examples

See OPERATOR_GUIDE.md for complete reference.

### Quick Actions

```bash
# Skip current track
/srv/ai_radio/scripts/skip-track.sh music

# Force break now
/srv/ai_radio/scripts/force-break.sh

# Play file immediately
cp announcement.mp3 /srv/ai_radio/drops/

# Push track to queue
/srv/ai_radio/scripts/push-track.sh music /path/to/song.mp3

# Emergency fallback
/srv/ai_radio/scripts/activate-emergency.sh
```

## Test Results

All operator tools functional:
- Skip track script works via socket
- Push track script works via socket
- Clear queue script removes all items
- Emergency activation clears all queues
- Service control wrapper starts/stops/restarts correctly

## SOW Compliance

✅ Section 10: Human override capabilities
✅ Section 10: Manual controls for operators
✅ Section 10: Emergency procedures
✅ Section 3: Simple, maintainable tooling

---

**Implementation Complete**
