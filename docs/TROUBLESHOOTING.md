# Troubleshooting Guide

Comprehensive issue diagnosis and resolution for AI Radio Station.

---

## Quick Diagnosis

Start here. Identify your symptom and jump to the relevant section.

| Symptom | Likely Cause | Quick Check | Jump To |
|---------|--------------|-------------|---------|
| Stream not accessible | Icecast or Liquidsoap down | `systemctl status icecast2 ai-radio-liquidsoap` | [Stream Issues](#stream-issues) |
| No music playing | Empty queue, no tracks in DB | `echo "music.queue" \| nc -U /run/liquidsoap/radio.sock` | [Playback Issues](#playback-issues) |
| Breaks not playing | Break generation failed, API keys | `journalctl -u ai-radio-break-scheduler -n 20` | [Break Issues](#break-issues) |
| Station IDs interrupting mid-track | Buffer issue, track_sensitive | Check `config/radio.liq` for buffer | [Station ID Issues](#station-id-issues) |
| Web player not updating | Export timer down, JSON stale | `cat /srv/ai_radio/public/now_playing.json` | [Frontend Issues](#frontend-issues) |
| High CPU usage | Too many tracks queued, busy loop | `ps aux \| grep liquidsoap` | [Performance Issues](#performance-issues) |
| Database locked | Concurrent access | `lsof /srv/ai_radio/db/radio.sqlite3` | [Database Issues](#database-issues) |

---

## Stream Issues

### Symptom: Stream URL Returns 404 or Connection Refused

**Quick check:**
```bash
curl -I http://localhost:8000/radio
```

**Diagnosis:**

1. **Is Icecast running?**
   ```bash
   sudo systemctl status icecast2
   ```

   **If inactive:** Start it
   ```bash
   sudo systemctl start icecast2
   ```

2. **Is Liquidsoap running?**
   ```bash
   sudo systemctl status ai-radio-liquidsoap
   ```

   **If failed:** Check logs
   ```bash
   sudo journalctl -u ai-radio-liquidsoap -n 50
   ```

3. **Is Liquidsoap connected to Icecast?**
   Check Liquidsoap logs for connection messages:
   ```bash
   sudo journalctl -u ai-radio-liquidsoap | grep -i "connected\|icecast"
   ```

   Look for: `"Connected to Icecast"`

   **If not connected:** Check Icecast password
   ```bash
   cat /srv/ai_radio/.icecast_secrets
   ```

   Verify it matches `/etc/icecast2/icecast.xml`:
   ```bash
   sudo grep source-password /etc/icecast2/icecast.xml
   ```

**Common causes:**

- **Icecast not running** → Start: `sudo systemctl start icecast2`
- **Wrong source password** → Update `.icecast_secrets` or `icecast.xml`
- **Port 8000 blocked** → Check firewall: `sudo ufw allow 8000/tcp`
- **Liquidsoap config error** → Test: `liquidsoap --check /srv/ai_radio/config/radio.liq`

---

### Symptom: Stream Plays But Skips/Stutters

**Diagnosis:**

1. **Check CPU usage:**
   ```bash
   top -p $(pgrep liquidsoap)
   ```

   **If >80%:** See [Performance Issues](#performance-issues)

2. **Check network bandwidth:**
   ```bash
   iftop -i eth0
   ```

   **If saturated:** Reduce streaming bitrate in `config/radio.liq`:
   ```liquidsoap
   %mp3(bitrate=96)  # Down from 128
   ```

3. **Check disk I/O:**
   ```bash
   iostat -x 1 5
   ```

   **If high wait times:** Music files on slow disk? Check mount:
   ```bash
   df -h /srv/ai_radio/assets/music
   ```

**Solutions:**

- Lower streaming bitrate (edit `config/radio.liq`)
- Reduce queue depth (edit `enqueue_music.py`)
- Move assets to faster disk
- Increase Liquidsoap buffer (edit `config/radio.liq`)

---

## Playback Issues

### Symptom: No Music Playing (Silence)

**Quick diagnosis:**
```bash
# Check music queue
echo "music.queue" | nc -U /run/liquidsoap/radio.sock

# Check track count in database
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM assets WHERE kind='music';"

# Check recent play history
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT * FROM play_history ORDER BY played_at DESC LIMIT 5;"
```

**Cause 1: Music queue is empty**

**Solution:**
```bash
# Manually enqueue music
cd /srv/ai_radio
.venv/bin/python scripts/enqueue_music.py

# Check if enqueue timer is running
systemctl status ai-radio-enqueue.timer

# If not running, start it
sudo systemctl start ai-radio-enqueue.timer
```

**Cause 2: No tracks in database**

**Solution:**
```bash
# Check music directory
ls -lh /srv/ai_radio/assets/music/

# If empty, ingest music
./scripts/batch_ingest.sh /path/to/music/

# Verify ingestion
sqlite3 /srv/ai_radio/db/radio.sqlite3 \
  "SELECT COUNT(*) FROM assets WHERE kind='music';"
```

**Cause 3: Liquidsoap not playing from queue**

**Check Liquidsoap logs:**
```bash
sudo journalctl -u ai-radio-liquidsoap -n 50
```

Look for errors like:
- `"Failed to decode"` → Audio file corrupted
- `"File not found"` → Path mismatch between DB and filesystem
- `"No tracks available"` → Track selection failing

---

### Symptom: Same Songs Playing Over and Over

**Diagnosis:**

1. **Check recently played list:**
   ```bash
   cd /srv/ai_radio
   .venv/bin/python scripts/diagnose_track_selection.py
   ```

   Shows recently played tracks and available tracks.

2. **Check track count:**
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "SELECT COUNT(*) FROM assets WHERE kind='music';"
   ```

   **If <50 tracks:** Library too small, more variety needed

3. **Check play history recording:**
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "SELECT COUNT(*) FROM play_history WHERE played_at > datetime('now', '-1 hour');"
   ```

   **If 0:** Play history not recording, `record_play.py` not working

**Solutions:**

- **Add more music:** Ingest more tracks
- **Verify `record_play.py` is called:** Check Liquidsoap config has `on_track` callback
- **Reduce `RECENT_HISTORY_SIZE`:** If library <50 tracks, edit `enqueue_music.py`:
  ```python
  RECENT_HISTORY_SIZE = 10  # Down from 20
  ```

---

### Symptom: Low Energy Songs Playing During High Energy Hours

**Diagnosis:**

Energy flow algorithm selects tracks based on time of day. Check if:

1. **Energy levels are calculated:**
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "SELECT AVG(energy_level), MIN(energy_level), MAX(energy_level) FROM assets WHERE kind='music';"
   ```

   **If NULL:** Energy not computed, re-ingest music

2. **Energy flow is working:**
   ```bash
   cd /srv/ai_radio
   .venv/bin/python scripts/diagnose_track_selection.py
   ```

   Shows energy flow computation for current time

**Solutions:**

- Re-ingest music with energy computation
- Adjust energy flow curve in `src/ai_radio/track_selection.py`

---

## Break Issues

### Symptom: Breaks Not Playing

**Quick check:**
```bash
# Check break scheduler timer
systemctl status ai-radio-break-scheduler.timer

# Check break files exist
ls -lh /srv/ai_radio/assets/breaks/

# Check breaks queue
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock
```

**Cause 1: Break generation failing**

**Check logs:**
```bash
sudo journalctl -u ai-radio-break-scheduler -n 50
```

Look for errors:
- `"API key not found"` → Missing API key
- `"Rate limit"` → Too many API requests
- `"No news items"` → RSS feeds down
- `"TTS failed"` → Voice synthesis error

**Solutions:**

- **Missing API keys:** Add to `.env`:
  ```bash
  RADIO_LLM_API_KEY=sk-ant-api03-YOUR-KEY
  RADIO_GEMINI_API_KEY=YOUR-GEMINI-KEY
  ```

- **Rate limit:** Check quota:
  ```bash
  .venv/bin/python scripts/check_gemini_quota.py
  ```

  Reduce break frequency in timer:
  ```bash
  sudo systemctl edit ai-radio-break-scheduler.timer
  # Change OnCalendar=hourly to less frequent
  ```

- **RSS feeds down:** Test feeds manually:
  ```bash
  curl -I https://your-news-feed.com/rss
  ```

  Update feeds in `.env` if needed

**Cause 2: Breaks generated but not queued**

**Check scheduler logs:**
```bash
sudo journalctl -u ai-radio-break-scheduler -n 20
```

Look for: `"Break already queued, skipping"`

**Solution:** Clear stale break from queue:
```bash
echo "breaks.clear" | nc -U /run/liquidsoap/radio.sock
```

**Cause 3: Timer not running**

**Check timer status:**
```bash
systemctl list-timers ai-radio-break-scheduler.timer
```

**If not listed:** Enable and start:
```bash
sudo systemctl enable --now ai-radio-break-scheduler.timer
```

---

### Symptom: Breaks Playing But Audio is Garbled/Corrupted

**Diagnosis:**

1. **Listen to break file directly:**
   ```bash
   # Find most recent break
   ls -lt /srv/ai_radio/assets/breaks/break_*.mp3 | head -1

   # Play it
   mpv /srv/ai_radio/assets/breaks/break_20251223_120000.mp3
   ```

2. **Check file size:**
   ```bash
   ls -lh /srv/ai_radio/assets/breaks/break_*.mp3
   ```

   **If <100KB:** Generation incomplete or failed

**Solutions:**

- **TTS provider issue:** Switch providers in `.env`:
  ```bash
  RADIO_TTS_PROVIDER=openai  # Or gemini
  ```

- **FFmpeg mixing error:** Check logs for FFmpeg errors:
  ```bash
  sudo journalctl -u ai-radio-break-scheduler | grep -i ffmpeg
  ```

- **Regenerate break manually:**
  ```bash
  cd /srv/ai_radio
  .venv/bin/python scripts/generate_break.py
  ```

---

### Symptom: Breaks Cut Off Mid-Sentence

**Cause:** Audio mixing issue - voice longer than bed

**Diagnosis:**

Check bed duration vs script duration:
```bash
# Get bed duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \
  /srv/ai_radio/assets/beds/your_bed.mp3

# Compare to break duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \
  /srv/ai_radio/assets/breaks/break_latest.mp3
```

**Solutions:**

- **Use longer beds** (4-5 minutes recommended)
- **Reduce script length:** Adjust in `.env`:
  ```bash
  RADIO_MAX_NEWS_ITEMS=3  # Down from 5
  ```
- **Adjust bed timing:** Edit `.env`:
  ```bash
  RADIO_BED_POSTROLL_SECONDS=10.0  # Up from 5.4
  ```

---

## Station ID Issues

### Symptom: Station IDs Interrupting Music Mid-Track

**Root cause:** Breaks queue has buffer, causing immediate playback

**Check configuration:**
```bash
grep "break_queue" /srv/ai_radio/config/radio.liq
```

**Should show:**
```liquidsoap
break_queue = request.queue(id="breaks")
```

**Should NOT show:**
```liquidsoap
break_queue = buffer(request.queue(id="breaks"))  # BAD - causes interruption
```

**Solution:**

1. **Remove buffer from breaks queue:**
   Edit `/srv/ai_radio/config/radio.liq`:
   ```liquidsoap
   break_queue = request.queue(id="breaks")
   ```

2. **Ensure track_sensitive is set:**
   ```liquidsoap
   radio = fallback(track_sensitive=true, [break_queue, music_queue])
   ```

3. **Restart Liquidsoap:**
   ```bash
   sudo systemctl restart ai-radio-liquidsoap
   ```

---

### Symptom: Station IDs Not Playing

**Quick check:**
```bash
# Check timer status
systemctl status ai-radio-schedule-station-id.timer

# Check station ID files exist
ls -lh /srv/ai_radio/assets/bumpers/

# Check breaks queue (station IDs use breaks queue)
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock
```

**Common causes:**

1. **Timer not running:**
   ```bash
   sudo systemctl enable --now ai-radio-schedule-station-id.timer
   ```

2. **No station ID files:**
   Check for files matching `station_id_*.mp3`:
   ```bash
   ls /srv/ai_radio/assets/bumpers/station_id_*
   ```

   **If empty:** Add station ID files (5-15 seconds, MP3 or WAV)

3. **Scheduler state locked:**
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "SELECT * FROM scheduler_state WHERE key='station_id_scheduled';"
   ```

   **If shows current time:** Clear state:
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "DELETE FROM scheduler_state WHERE key='station_id_scheduled';"
   ```

---

## Frontend Issues

### Symptom: Web Player Shows Stale "Now Playing" Info

**Diagnosis:**

1. **Check export timer:**
   ```bash
   systemctl status ai-radio-export-nowplaying.timer
   ```

2. **Check JSON file:**
   ```bash
   ls -lh /srv/ai_radio/public/now_playing.json
   cat /srv/ai_radio/public/now_playing.json | jq .
   ```

   Look at modification time. Should update every 10 seconds.

3. **Check if script runs:**
   ```bash
   sudo journalctl -u ai-radio-export-nowplaying -n 10
   ```

**Solutions:**

- **Timer not running:**
  ```bash
  sudo systemctl enable --now ai-radio-export-nowplaying.timer
  ```

- **Script failing:**
  Run manually to see errors:
  ```bash
  cd /srv/ai_radio
  .venv/bin/python scripts/export_now_playing.py
  ```

- **Liquidsoap socket not accessible:**
  Check permissions:
  ```bash
  ls -l /run/liquidsoap/radio.sock
  sudo chmod 660 /run/liquidsoap/radio.sock
  ```

---

### Symptom: Web Player Not Loading (404)

**Diagnosis:**

1. **Check nginx is running:**
   ```bash
   sudo systemctl status nginx
   ```

2. **Check frontend files exist:**
   ```bash
   ls -lh /srv/ai_radio/public/index.html
   ls -lh /srv/ai_radio/public/now_playing.json
   ```

3. **Check nginx config:**
   ```bash
   sudo nginx -t
   ```

**Solutions:**

- **Nginx not running:**
  ```bash
  sudo systemctl start nginx
  ```

- **Frontend files missing:**
  ```bash
  ./scripts/deploy.sh frontend
  ```

- **Nginx config error:**
  ```bash
  sudo journalctl -u nginx -n 20
  ```

---

## Database Issues

### Symptom: "Database is Locked" Errors

**Cause:** Multiple processes trying to write to SQLite simultaneously

**Diagnosis:**

Find processes using database:
```bash
sudo lsof /srv/ai_radio/db/radio.sqlite3
```

**Solutions:**

1. **Wait and retry** - Usually resolves in 1-2 seconds

2. **Increase timeout in scripts:**
   Edit scripts to use longer timeout:
   ```python
   conn = sqlite3.connect(config.db_path, timeout=10.0)
   ```

3. **Kill stuck processes:**
   ```bash
   # Find PID from lsof output
   sudo kill -9 <PID>
   ```

4. **Stop competing services temporarily:**
   ```bash
   sudo systemctl stop ai-radio-enqueue.timer ai-radio-export-nowplaying.timer
   # Do database work
   sudo systemctl start ai-radio-enqueue.timer ai-radio-export-nowplaying.timer
   ```

---

### Symptom: Database Corruption (integrity_check fails)

**Diagnosis:**
```bash
sqlite3 /srv/ai_radio/db/radio.sqlite3 "PRAGMA integrity_check;"
```

**If shows errors:** Database is corrupted

**Recovery:**

1. **Stop all services:**
   ```bash
   sudo systemctl stop ai-radio-liquidsoap ai-radio-enqueue.timer ai-radio-export-nowplaying.timer
   ```

2. **Backup corrupted database:**
   ```bash
   cp /srv/ai_radio/db/radio.sqlite3 /srv/ai_radio/db/radio.sqlite3.corrupted
   ```

3. **Attempt repair:**
   ```bash
   # Export good data
   sqlite3 /srv/ai_radio/db/radio.sqlite3 .dump > /tmp/radio_dump.sql

   # Create new database
   rm /srv/ai_radio/db/radio.sqlite3
   sqlite3 /srv/ai_radio/db/radio.sqlite3 < /tmp/radio_dump.sql
   ```

4. **If repair fails, restore from backup:**
   ```bash
   cp /srv/ai_radio/backups/radio.sqlite3 /srv/ai_radio/db/radio.sqlite3
   ```

5. **Set permissions:**
   ```bash
   chown ai-radio:ai-radio /srv/ai_radio/db/radio.sqlite3
   chmod 644 /srv/ai_radio/db/radio.sqlite3
   ```

6. **Restart services:**
   ```bash
   sudo systemctl start ai-radio-liquidsoap ai-radio-enqueue.timer ai-radio-export-nowplaying.timer
   ```

---

## Performance Issues

### Symptom: High CPU Usage

**Diagnosis:**

1. **Check Liquidsoap CPU:**
   ```bash
   top -p $(pgrep liquidsoap)
   ```

2. **Check for busy loops:**
   ```bash
   sudo journalctl -u ai-radio-liquidsoap -n 100 | grep -i error
   ```

**Common causes and solutions:**

1. **Too many tracks queued:**
   ```bash
   echo "music.queue" | nc -U /run/liquidsoap/radio.sock | wc -l
   ```

   **If >20:** Reduce `TARGET_QUEUE_DEPTH` in `enqueue_music.py`

2. **Audio processing overhead:**
   Edit `config/radio.liq` to reduce processing:
   ```liquidsoap
   # Disable normalization temporarily
   # music_queue = normalize(music_queue)
   ```

3. **Crossfade complexity:**
   Reduce crossfade duration:
   ```liquidsoap
   music_queue = crossfade(duration=2.0, music_queue)  # Down from 4.0
   ```

---

### Symptom: High Memory Usage

**Check memory:**
```bash
ps aux | grep liquidsoap
free -h
```

**Solutions:**

1. **Restart Liquidsoap weekly:**
   Add to cron:
   ```bash
   0 3 * * 0 systemctl restart ai-radio-liquidsoap
   ```

2. **Reduce buffer sizes in `config/radio.liq`:**
   ```liquidsoap
   set("frame.duration", 0.04)  # Smaller frame size
   ```

---

### Symptom: Disk Space Running Low

**Check usage:**
```bash
df -h /srv/ai_radio
du -sh /srv/ai_radio/*
```

**Cleanup:**

1. **Old breaks:**
   ```bash
   find /srv/ai_radio/assets/breaks/archive/ -mtime +7 -delete
   ```

2. **Old play history:**
   ```bash
   sqlite3 /srv/ai_radio/db/radio.sqlite3 \
     "DELETE FROM play_history WHERE played_at < datetime('now', '-30 days');"
   ```

3. **Logs:**
   ```bash
   sudo journalctl --vacuum-time=7d
   ```

---

## API Issues

### Symptom: Break Generation Fails with "Rate Limit Exceeded"

**Diagnosis:**

Check Gemini quota:
```bash
cd /srv/ai_radio
.venv/bin/python scripts/check_gemini_quota.py
```

**Solutions:**

1. **Wait for quota reset** (usually 1 hour)

2. **Reduce break frequency:**
   ```bash
   sudo systemctl edit ai-radio-break-scheduler.timer
   # Change to every 2 hours: OnCalendar=0/2:59
   ```

3. **Switch TTS provider:**
   Edit `.env`:
   ```bash
   RADIO_TTS_PROVIDER=openai
   RADIO_TTS_API_KEY=sk-your-openai-key
   ```

---

### Symptom: "Invalid API Key" Errors

**Diagnosis:**

Check API keys are set:
```bash
cd /srv/ai_radio
.venv/bin/python -c "
from ai_radio.config import config
print('LLM:', config.llm_api_key[:10] if config.llm_api_key else 'NOT SET')
print('Gemini:', config.gemini_api_key[:10] if config.gemini_api_key else 'NOT SET')
"
```

**Solutions:**

1. **Add missing keys to `.env`:**
   ```bash
   nano /srv/ai_radio/.env
   ```

   Add:
   ```bash
   RADIO_LLM_API_KEY=sk-ant-api03-YOUR-KEY
   RADIO_GEMINI_API_KEY=YOUR-GEMINI-KEY
   ```

2. **Verify keys are valid:**
   - Claude: https://console.anthropic.com/
   - Gemini: https://aistudio.google.com/

3. **Restart services:**
   ```bash
   sudo systemctl restart ai-radio-break-scheduler.timer
   ```

---

## Network Issues

### Symptom: Can't Access Stream from External Network

**Diagnosis:**

1. **Test from server:**
   ```bash
   curl -I http://localhost:8000/radio
   ```

   **If works locally:** Network/firewall issue

2. **Check firewall:**
   ```bash
   sudo ufw status | grep 8000
   ```

   **If not listed:** Allow port:
   ```bash
   sudo ufw allow 8000/tcp
   ```

3. **Check Icecast listening:**
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

   Should show: `0.0.0.0:8000` (all interfaces)

4. **Test from external:**
   ```bash
   curl -I http://YOUR-SERVER-IP:8000/radio
   ```

**Solutions:**

- **Firewall blocking:** Allow port 8000
- **Cloud security groups:** Check cloud provider firewall
- **Icecast bound to localhost:** Edit `/etc/icecast2/icecast.xml`:
  ```xml
  <bind-address>0.0.0.0</bind-address>
  ```

---

### Symptom: Web Player Can't Load Stream (CORS Error)

**Check browser console for:**
```
Access to fetch at 'http://server:8000/radio' has been blocked by CORS policy
```

**Solution:**

Edit `/etc/icecast2/icecast.xml`:
```xml
<http-headers>
  <header name="Access-Control-Allow-Origin" value="*" />
</http-headers>
```

Restart Icecast:
```bash
sudo systemctl restart icecast2
```

---

## Permission Issues

### Symptom: "Permission Denied" Errors

**Common causes:**

1. **File ownership wrong:**
   ```bash
   sudo chown -R ai-radio:ai-radio /srv/ai_radio
   ```

2. **Socket not accessible:**
   ```bash
   sudo chown ai-radio:ai-radio /run/liquidsoap/radio.sock
   sudo chmod 660 /run/liquidsoap/radio.sock
   ```

3. **Script not executable:**
   ```bash
   chmod +x /srv/ai_radio/scripts/*.py
   chmod +x /srv/ai_radio/scripts/*.sh
   ```

4. **User not in ai-radio group:**
   ```bash
   sudo usermod -aG ai-radio $USER
   # Log out and back in for group change to take effect
   ```

---

## Known Issues and Workarounds

### Issue: Station ID Plays with Same Timestamp as Music Track

**Status:** Fixed in 2025-12-22 via timestamp format consistency

**Symptom:** Play history shows break/station ID with same timestamp as music track, causing wrong order in recent plays

**Workaround (if on old version):**
```bash
cd /srv/ai_radio
.venv/bin/python scripts/fix_timestamp_formats.py
```

---

### Issue: Liquidsoap High Memory After Days of Running

**Status:** Known limitation of Liquidsoap

**Workaround:** Restart weekly via cron:
```bash
0 3 * * 0 systemctl restart ai-radio-liquidsoap
```

---

### Issue: Break Audio Cuts Off During Long News Segment

**Status:** By design - beds have fixed length

**Workaround:** Use longer beds (5+ minutes) or reduce news items:
```bash
RADIO_MAX_NEWS_ITEMS=3  # In .env
```

---

## Escalation and Getting Help

### Gather Diagnostic Info

Before asking for help, gather this info:

```bash
# System info
cat /etc/os-release
uname -a

# Service status
systemctl status 'ai-radio-*' > /tmp/status.txt

# Recent logs (last hour)
sudo journalctl -u ai-radio-liquidsoap --since "1 hour ago" > /tmp/liquidsoap.log
sudo journalctl -u ai-radio-enqueue --since "1 hour ago" > /tmp/enqueue.log
sudo journalctl -u ai-radio-break-scheduler --since "1 hour ago" > /tmp/breaks.log

# Queue status
echo "music.queue" | nc -U /run/liquidsoap/radio.sock > /tmp/music_queue.txt
echo "breaks.queue" | nc -U /run/liquidsoap/radio.sock > /tmp/breaks_queue.txt

# Database stats
sqlite3 /srv/ai_radio/db/radio.sqlite3 "
  SELECT 'Music tracks:', COUNT(*) FROM assets WHERE kind='music' UNION ALL
  SELECT 'Recent plays:', COUNT(*) FROM play_history WHERE played_at > datetime('now', '-1 hour');
" > /tmp/db_stats.txt

# Configuration (redact API keys!)
grep -v API_KEY /srv/ai_radio/.env > /tmp/config_redacted.txt
```

---

### Where to Get Help

- **GitHub Issues:** [Your repo URL]
- **Documentation:** See `docs/` directory
- **Logs:** Always include relevant logs when asking for help

---

## See Also

- [Administration Guide](ADMINISTRATION.md) - Day-to-day operations
- [Scripts Reference](SCRIPTS.md) - Detailed script documentation
- [Configuration Guide](CONFIGURATION.md) - Environment variables
- [Deployment Guide](DEPLOYMENT.md) - Initial setup
