# Administration Guide

Day-to-day operations and maintenance for your AI Radio Station.

---

## Quick Reference

| Task | Command |
|------|---------|
| Check service status | `sudo systemctl status ai-radio-liquidsoap` |
| Restart streaming | `sudo systemctl restart ai-radio-liquidsoap` |
| View live logs | `sudo journalctl -u ai-radio-liquidsoap -f` |
| Check queue depth | `echo "music.queue" | nc -U /run/liquidsoap/radio.sock` |
| Skip current track | `echo "music.skip" | nc -U /run/liquidsoap/radio.sock` |
| Trigger break now | `.venv/bin/python scripts/schedule_break.py` |
| Health check | `.venv/bin/python scripts/health_check.py` |

---

## Service Management

### Checking Status

**Check all services:**
```bash
systemctl status 'ai-radio-*'
```

**Check specific service:**
```bash
sudo systemctl status ai-radio-liquidsoap
sudo systemctl status ai-radio-enqueue.timer
```

**List all timers:**
```bash
systemctl list-timers ai-radio-*
```

**What you'll see:**

- `●` green = active (running)
- `●` red = failed
- `○` white = inactive/stopped

**Timer services (oneshot):**
Timers trigger oneshot services. The service itself may show as "inactive" or "failed" - this is normal. The timer status is what matters.

✅ **Good:** `ai-radio-enqueue.timer` = active (waiting)
✅ **Good:** `ai-radio-enqueue.service` = inactive (dead) - ran successfully, waiting for next trigger
⚠ **Warning:** `ai-radio-enqueue.service` = failed - check logs
❌ **Bad:** `ai-radio-enqueue.timer` = inactive (dead) - timer not running

---

### Starting and Stopping

**Start services:**
```bash
# Start streaming engine
sudo systemctl start ai-radio-liquidsoap

# Start all timers
sudo systemctl start ai-radio-enqueue.timer
sudo systemctl start ai-radio-schedule-station-id.timer
sudo systemctl start ai-radio-break-scheduler.timer
sudo systemctl start ai-radio-export-nowplaying.timer
```

**Stop services:**
```bash
# Stop streaming (interrupts stream)
sudo systemctl stop ai-radio-liquidsoap

# Stop specific timer
sudo systemctl stop ai-radio-enqueue.timer
```

**Restart services:**
```bash
# Restart streaming engine (brief interruption)
sudo systemctl restart ai-radio-liquidsoap

# Restart timer (resets schedule)
sudo systemctl restart ai-radio-enqueue.timer
```

**Enable/disable automatic startup:**
```bash
# Enable (start on boot)
sudo systemctl enable ai-radio-liquidsoap

# Disable (don't start on boot)
sudo systemctl disable ai-radio-liquidsoap
```

---

### Service Dependencies

Services should start in this order:

1. **Icecast2** - Streaming server must be running first
2. **ai-radio-liquidsoap** - Audio streaming engine
3. **Timers** - Queue management, breaks, station IDs

**Start everything:**
```bash
# 1. Ensure Icecast is running
sudo systemctl start icecast2

# 2. Start Liquidsoap
sudo systemctl start ai-radio-liquidsoap

# 3. Start all timers
sudo systemctl start ai-radio-enqueue.timer \
                     ai-radio-schedule-station-id.timer \
                     ai-radio-break-scheduler.timer \
                     ai-radio-export-nowplaying.timer
```

**Stop everything (graceful shutdown):**
```bash
# 1. Stop timers first (prevents new tracks from queuing)
sudo systemctl stop ai-radio-enqueue.timer \
                    ai-radio-schedule-station-id.timer \
                    ai-radio-break-scheduler.timer \
                    ai-radio-export-nowplaying.timer

# 2. Stop Liquidsoap (finishes current track)
sudo systemctl stop ai-radio-liquidsoap

# 3. Optionally stop Icecast
sudo systemctl stop icecast2
```

---

## Monitoring

### Viewing Logs

**Real-time log monitoring:**
```bash
# Liquidsoap streaming engine
sudo journalctl -u ai-radio-liquidsoap -f

# Music enqueue service
sudo journalctl -u ai-radio-enqueue -f

# Break scheduler
sudo journalctl -u ai-radio-break-scheduler -f

# All ai-radio services
sudo journalctl -u 'ai-radio-*' -f
```

**Recent log entries:**
```bash
# Last 50 entries from Liquidsoap
sudo journalctl -u ai-radio-liquidsoap -n 50

# Last hour of logs
sudo journalctl -u ai-radio-liquidsoap --since "1 hour ago"

# Logs from specific time range
sudo journalctl -u ai-radio-liquidsoap --since "2025-12-22 14:00" --until "2025-12-22 15:00"
```

**Search logs for errors:**
```bash
# Find errors in Liquidsoap
sudo journalctl -u ai-radio-liquidsoap | grep -i error

# Find warnings and errors
sudo journalctl -u ai-radio-liquidsoap | grep -iE "error|warning|failed"
```

**Export logs:**
```bash
# Save last 1000 lines to file
sudo journalctl -u ai-radio-liquidsoap -n 1000 > /tmp/liquidsoap.log
```

---

### Checking Queue Status

**Music queue:**
```bash
# Get queue contents
echo "music.queue" | nc -U /run/liquidsoap/radio.sock

# Count tracks in queue
echo "music.queue" | nc -U /run/liquidsoap/radio.sock | grep -c "^[0-9]"
```

**Breaks queue:**
```bash
# Get breaks queue contents
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock

# Count breaks in queue
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock | grep -c "^[0-9]"
```

**What healthy queues look like:**

- **Music queue:** 3-8 tracks (target: 8)
- **Breaks queue:** 0-1 items (usually empty, fills just before break plays)

**Warning signs:**

- Music queue = 0 tracks → No music will play, check enqueue service
- Music queue > 20 tracks → Over-queuing, check enqueue logic
- Breaks queue > 3 items → Breaks backing up, check Liquidsoap `track_sensitive` setting

---

### Monitoring Playback

**Current track:**
```bash
# Get now playing info
cat /srv/ai_radio/public/now_playing.json | jq .current
```

**Play history (last 10):**
```bash
# Via database
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT datetime(played_at, 'localtime'), source,
          (SELECT title FROM assets WHERE id=asset_id)
   FROM play_history
   ORDER BY played_at DESC
   LIMIT 10;"
```

**Listen to stream:**
```bash
# Using mpv
mpv http://your-server:8000/radio

# Using ffplay
ffplay -nodisp http://your-server:8000/radio

# Using VLC
vlc http://your-server:8000/radio
```

---

### Health Checks

**Automated health check:**
```bash
cd /srv/ai_radio
.venv/bin/python scripts/health_check.py
```

**Manual health checks:**
```bash
# 1. Is Liquidsoap running?
sudo systemctl status ai-radio-liquidsoap

# 2. Are timers active?
systemctl list-timers ai-radio-*

# 3. Is music queue full?
echo "music.queue" | nc -U /run/liquidsoap/radio.sock

# 4. Recent play activity?
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM play_history WHERE played_at > datetime('now', '-10 minutes');"

# 5. Is stream accessible?
curl -I http://localhost:8000/radio
```

**Set up monitoring (cron):**
```bash
# Add to crontab
crontab -e

# Check health every 5 minutes
*/5 * * * * /srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/health_check.py || echo "AI Radio health check failed" | mail -s "Radio Alert" your-email@example.com
```

---

## Manual Interventions

### Queue Management

**Manually queue music:**
```bash
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_music.py
```

**Skip current track:**
```bash
# Skip currently playing music
echo "music.skip" | nc -U /run/liquidsoap/radio.sock

# Skip current break
echo "breaks.skip" | nc -U /run/liquidsoap/radio.sock
```

**Clear entire queue:**
```bash
# Clear music queue (use with caution!)
echo "music.clear" | nc -U /run/liquidsoap/radio.sock

# Clear breaks queue
echo "breaks.clear" | nc -U /run/liquidsoap/radio.sock
```

**Push specific track to queue:**
```bash
# Find track in database
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT id, path, title, artist FROM assets WHERE title LIKE '%Your Song%';"

# Push to queue
echo "music.push /srv/ai_radio/assets/music/abc123def456.mp3" | nc -U /run/liquidsoap/radio.sock
```

---

### Break Management

**Trigger break immediately:**
```bash
# Generate and queue a break now (ignores schedule)
cd /srv/ai_radio
.venv/bin/python scripts/generate_break.py
.venv/bin/python scripts/schedule_break.py
```

**Skip upcoming break:**
```bash
# Clear breaks queue
echo "breaks.clear" | nc -U /run/liquidsoap/radio.sock

# Or temporarily disable break timer
sudo systemctl stop ai-radio-break-scheduler.timer
```

**Re-enable break timer:**
```bash
sudo systemctl start ai-radio-break-scheduler.timer
```

**Check when next break is scheduled:**
```bash
systemctl list-timers ai-radio-break-scheduler.timer
```

---

### Station ID Management

**Trigger station ID immediately:**
```bash
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_station_id.py
```

**Disable station IDs temporarily:**
```bash
sudo systemctl stop ai-radio-schedule-station-id.timer
```

**Re-enable station IDs:**
```bash
sudo systemctl start ai-radio-schedule-station-id.timer
```

---

## Routine Maintenance

### Log Management

**Check log sizes:**
```bash
# Systemd journal size
sudo journalctl --disk-usage

# Application logs
du -sh /srv/ai_radio/logs/
```

**Rotate logs:**
```bash
# Systemd automatically rotates journald logs
# Configure in /etc/systemd/journald.conf:
# SystemMaxUse=1G  # Keep max 1GB of logs

# Manually clean old logs (keeps last 7 days)
sudo journalctl --vacuum-time=7d

# Or keep only 500MB
sudo journalctl --vacuum-size=500M
```

**Clear application logs:**
```bash
# Backup first
cp /srv/ai_radio/logs/liquidsoap.log /srv/ai_radio/logs/liquidsoap.log.backup

# Truncate log file
truncate -s 0 /srv/ai_radio/logs/liquidsoap.log

# Or rotate with timestamps
mv /srv/ai_radio/logs/liquidsoap.log /srv/ai_radio/logs/liquidsoap.log.$(date +%Y%m%d)
```

---

### Database Maintenance

**Check database size:**
```bash
ls -lh /srv/ai_radio/db/radio.sqlite3
```

**Vacuum database (reclaim space):**
```bash
# Stop services that access database
sudo systemctl stop ai-radio-enqueue.timer \
                    ai-radio-break-scheduler.timer \
                    ai-radio-schedule-station-id.timer \
                    ai-radio-export-nowplaying.timer

# Vacuum
sqlite3 /srv/ai_radio/db/radio.sqlite3 "VACUUM;"

# Restart services
sudo systemctl start ai-radio-enqueue.timer \
                     ai-radio-break-scheduler.timer \
                     ai-radio-schedule-station-id.timer \
                     ai-radio-export-nowplaying.timer
```

**Archive old play history:**
```bash
# Export history older than 90 days
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT * FROM play_history WHERE played_at < datetime('now', '-90 days');" \
  > /srv/ai_radio/backups/play_history_archive_$(date +%Y%m%d).csv

# Delete old history (keeps last 90 days)
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "DELETE FROM play_history WHERE played_at < datetime('now', '-90 days');"
```

**Integrity check:**
```bash
sqlite3 /srv/ai_radio/db/radio.sqlite3 "PRAGMA integrity_check;"
```

---

### Break File Management

**Check break directory size:**
```bash
du -sh /srv/ai_radio/assets/breaks/
du -sh /srv/ai_radio/assets/breaks/archive/
```

**Manually archive old breaks:**
```bash
# Move breaks older than 60 minutes to archive
find /srv/ai_radio/assets/breaks/ -name "break_*.mp3" -mmin +60 \
  -exec mv {} /srv/ai_radio/assets/breaks/archive/ \;
```

**Clean up old archived breaks:**
```bash
# Delete archived breaks older than 30 days
find /srv/ai_radio/assets/breaks/archive/ -name "break_*.mp3" -mtime +30 -delete
```

**Note:** `schedule_break.py` automatically archives breaks when queuing new ones, so manual archival is rarely needed.

---

### Music Library Management

**Check music library size:**
```bash
# File count
ls -1 /srv/ai_radio/assets/music/ | wc -l

# Disk usage
du -sh /srv/ai_radio/assets/music/

# Database count
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM assets WHERE kind='music';"
```

**Add new music:**
```bash
# Ingest new tracks
./scripts/batch_ingest.sh /path/to/new/music

# Verify addition
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM assets WHERE kind='music' AND created_at > datetime('now', '-1 hour');"
```

**Remove track:**
```bash
# Find track ID
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT id, path, title, artist FROM assets WHERE title='Track to Remove';"

# Delete from database
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "DELETE FROM assets WHERE id='abc123def456';"

# Delete file
rm /srv/ai_radio/assets/music/abc123def456.mp3
```

**Regenerate track metadata:**
```bash
# If you fix tags in files, re-ingest
./scripts/batch_ingest.sh --force /srv/ai_radio/assets/music/
```

---

## Configuration Changes

### Updating .env Configuration

**Edit configuration:**
```bash
nano /srv/ai_radio/.env
```

**Which changes require restart:**

| Change | Requires Restart? |
|--------|------------------|
| API keys | ✅ Yes - Restart timers |
| Station name/location | ✅ Yes - Restart Liquidsoap |
| TTS voice/provider | ✅ Yes - Restart timers |
| News feeds | ✅ Yes - Restart break scheduler |
| Energy level/vibe | ⚠ No - Takes effect on next break |
| Audio timing (beds, crossfades) | ✅ Yes - Restart Liquidsoap |
| Break/music schedule | ✅ Yes - Restart timers |

**Restart services after config changes:**
```bash
# If you changed Liquidsoap variables (station name, paths, etc.)
sudo systemctl restart ai-radio-liquidsoap

# If you changed API keys or script generation settings
sudo systemctl restart ai-radio-break-scheduler.timer
sudo systemctl restart ai-radio-enqueue.timer
```

**Validate configuration:**
```bash
# Test config loads without errors
cd /srv/ai_radio
.venv/bin/python -c "from ai_radio.config import config; print(config.station_name)"
```

---

### Updating Liquidsoap Configuration

**Edit Liquidsoap config:**
```bash
nano /srv/ai_radio/config/radio.liq
```

**Test configuration syntax:**
```bash
liquidsoap --check /srv/ai_radio/config/radio.liq
```

**Apply changes:**
```bash
# Restart Liquidsoap (brief stream interruption)
sudo systemctl restart ai-radio-liquidsoap

# Verify it started successfully
sudo systemctl status ai-radio-liquidsoap
```

**Common config changes:**

- **Adjust crossfade duration** - Edit `crossfade_duration`
- **Change streaming bitrate** - Edit `%mp3` encoder settings
- **Modify normalization** - Edit `normalize` parameters
- **Adjust safety fallback** - Edit `safety` source

---

## Performance Tuning

### CPU and Memory Usage

**Check resource usage:**
```bash
# Overall system resources
htop

# Specific to AI Radio processes
ps aux | grep -E 'liquidsoap|ai-radio'

# Memory usage
free -h
```

**Optimize for limited resources:**

1. **Reduce music queue depth** (edit `enqueue_music.py`):
   ```python
   TARGET_QUEUE_DEPTH = 5  # Down from 8
   ```

2. **Reduce break generation frequency** (edit timer):
   ```bash
   sudo systemctl edit ai-radio-break-scheduler.timer
   # Change OnCalendar=hourly to less frequent
   ```

3. **Lower streaming bitrate** (edit `config/radio.liq`):
   ```liquidsoap
   %mp3(bitrate=96)  # Down from 128
   ```

---

### Disk Space Management

**Check disk usage:**
```bash
df -h /srv/ai_radio
du -sh /srv/ai_radio/*
```

**Optimize disk usage:**

1. **Clean old breaks:**
   ```bash
   find /srv/ai_radio/assets/breaks/archive/ -mtime +7 -delete
   ```

2. **Archive play history:**
   ```bash
   # Export to CSV
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     ".mode csv" ".output /srv/ai_radio/backups/history.csv" \
     "SELECT * FROM play_history WHERE played_at < datetime('now', '-30 days');"

   # Delete old records
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "DELETE FROM play_history WHERE played_at < datetime('now', '-30 days');"
   ```

3. **Compress old logs:**
   ```bash
   gzip /srv/ai_radio/logs/*.log.2025*
   ```

---

### Network Optimization

**Check streaming bandwidth:**
```bash
# Monitor bandwidth usage
iftop -i eth0

# Check active connections to Icecast
netstat -an | grep :8000
```

**Icecast tuning:**

Edit `/etc/icecast2/icecast.xml`:

```xml
<limits>
  <clients>100</clients>         <!-- Max concurrent listeners -->
  <sources>2</sources>           <!-- Max source connections -->
  <burst-size>65535</burst-size> <!-- Initial buffer size -->
</limits>
```

**Restart Icecast after changes:**
```bash
sudo systemctl restart icecast2
```

---

## Backup and Recovery

### Backing Up

**What to back up:**
1. Database (`db/radio.sqlite3`)
2. Configuration (`.env`, `config/radio.liq`)
3. Music library (`assets/music/`)
4. Station IDs (`assets/bumpers/`)
5. Background beds (`assets/beds/`)

**Backup script:**
```bash
#!/bin/bash
# /srv/ai_radio/scripts/backup.sh

BACKUP_DIR=/srv/ai_radio/backups
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai_radio_backup_$DATE"

mkdir -p $BACKUP_DIR/$BACKUP_NAME

# Database
sqlite3 /srv/ai_radio/db/radio.sqlite3 ".backup $BACKUP_DIR/$BACKUP_NAME/radio.sqlite3"

# Configuration
cp /srv/ai_radio/.env $BACKUP_DIR/$BACKUP_NAME/
cp /srv/ai_radio/config/radio.liq $BACKUP_DIR/$BACKUP_NAME/

# Compress
tar -czf $BACKUP_DIR/$BACKUP_NAME.tar.gz -C $BACKUP_DIR $BACKUP_NAME
rm -rf $BACKUP_DIR/$BACKUP_NAME

echo "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
```

**Automated backups (cron):**
```bash
# Daily backup at 3 AM
0 3 * * * /srv/ai_radio/scripts/backup.sh

# Keep only last 7 days of backups
0 4 * * * find /srv/ai_radio/backups/ -name "ai_radio_backup_*.tar.gz" -mtime +7 -delete
```

---

### Restoring

**Restore database:**
```bash
# Stop services
sudo systemctl stop ai-radio-liquidsoap ai-radio-enqueue.timer

# Restore from backup
cp /srv/ai_radio/backups/radio.sqlite3 /srv/ai_radio/db/radio.sqlite3

# Set permissions
chown ai-radio:ai-radio /srv/ai_radio/db/radio.sqlite3
chmod 644 /srv/ai_radio/db/radio.sqlite3

# Start services
sudo systemctl start ai-radio-liquidsoap ai-radio-enqueue.timer
```

**Restore configuration:**
```bash
# Restore .env
cp /srv/ai_radio/backups/.env /srv/ai_radio/.env

# Restore Liquidsoap config
cp /srv/ai_radio/backups/radio.liq /srv/ai_radio/config/radio.liq

# Restart services
sudo systemctl restart ai-radio-liquidsoap
```

---

## Emergency Procedures

### Stream is Down

**Quick recovery:**
```bash
# 1. Check if Icecast is running
sudo systemctl status icecast2
sudo systemctl restart icecast2

# 2. Restart Liquidsoap
sudo systemctl restart ai-radio-liquidsoap

# 3. Check queue has music
echo "music.queue" | nc -U /run/liquidsoap/radio.sock

# 4. Manually enqueue if empty
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_music.py

# 5. Verify stream is accessible
curl -I http://localhost:8000/radio
```

---

### No Music Playing (Queue Empty)

**Quick fix:**
```bash
# 1. Manually enqueue music
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_music.py

# 2. Check if music exists in database
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM assets WHERE kind='music';"

# 3. If no music, ingest some
./scripts/batch_ingest.sh /path/to/music

# 4. Restart enqueue timer
sudo systemctl restart ai-radio-enqueue.timer
```

---

### Break Generation Failing

**Diagnose and fix:**
```bash
# 1. Check recent logs
sudo journalctl -u ai-radio-break-scheduler -n 50

# 2. Test API keys
cd /srv/ai_radio
.venv/bin/python -c "from ai_radio.config import config; print(config.llm_api_key[:10])"

# 3. Manually generate break to see errors
.venv/bin/python scripts/generate_break.py

# 4. Check Gemini quota
.venv/bin/python scripts/check_gemini_quota.py
```

---

### Database Corruption

**Recovery:**
```bash
# 1. Stop services
sudo systemctl stop ai-radio-liquidsoap ai-radio-enqueue.timer

# 2. Check integrity
sqlite3 /srv/ai_radio/db/radio.sqlite3 "PRAGMA integrity_check;"

# 3. If corrupted, restore from backup
cp /srv/ai_radio/backups/radio.sqlite3 /srv/ai_radio/db/radio.sqlite3

# 4. If no backup, export and recreate
sqlite3 /srv/ai_radio/db/radio.sqlite3 .dump > /tmp/dump.sql
sqlite3 /srv/ai_radio/db/radio.sqlite3.new < /tmp/dump.sql
mv /srv/ai_radio/db/radio.sqlite3.new /srv/ai_radio/db/radio.sqlite3

# 5. Restart services
sudo systemctl start ai-radio-liquidsoap ai-radio-enqueue.timer
```

---

## Security

### Access Control

**File permissions:**
```bash
# Secure .env file
chmod 600 /srv/ai_radio/.env
chown ai-radio:ai-radio /srv/ai_radio/.env

# Secure Icecast password
chmod 600 /srv/ai_radio/.icecast_secrets
chown ai-radio:ai-radio /srv/ai_radio/.icecast_secrets

# Secure database
chmod 644 /srv/ai_radio/db/radio.sqlite3
chown ai-radio:ai-radio /srv/ai_radio/db/radio.sqlite3
```

**Socket permissions:**
```bash
# Liquidsoap socket (read/write for ai-radio group)
chown ai-radio:ai-radio /run/liquidsoap/radio.sock
chmod 660 /run/liquidsoap/radio.sock
```

---

### Firewall

**Check firewall status:**
```bash
sudo ufw status
```

**Allow only required ports:**
```bash
# Streaming
sudo ufw allow 8000/tcp

# Web interface
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSH (if needed)
sudo ufw allow 22/tcp
```

---

### API Key Rotation

**Update API keys:**

1. Get new keys from providers
2. Edit `.env`:
   ```bash
   nano /srv/ai_radio/.env
   ```
3. Update keys:
   ```bash
   RADIO_LLM_API_KEY=sk-ant-api03-NEW-KEY-HERE
   RADIO_GEMINI_API_KEY=NEW-GEMINI-KEY-HERE
   ```
4. Restart services:
   ```bash
   sudo systemctl restart ai-radio-break-scheduler.timer
   ```

---

## See Also

- [Scripts Reference](SCRIPTS.md) - Detailed script documentation
- [Configuration Guide](CONFIGURATION.md) - Environment variables
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Issue diagnosis *(coming soon)*
- [Deployment Guide](DEPLOYMENT.md) - Initial setup
