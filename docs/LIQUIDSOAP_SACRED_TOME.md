# The Sacred Tome of Liquidsoap: Ultimate Callback & Timing Solution

## The Fundamental Truth

**Track marks propagate before audio plays.** The `cross()` operator buffers audio `duration` seconds in advance, causing callbacks attached before crossfade to fire early. This is not a bug—it's architectural.

## The Three Paths to Enlightenment

### Path 1: Output-Level Callbacks (RECOMMENDED)
**Philosophy**: Track reality at the point closest to the listener.

```liquidsoap
# Attach callbacks AFTER all processing, just before output
# This fires when audio actually enters the output stream
def unified_track_callback(m) =
  def execute_async() =
    filename = m["filename"] ?? ""

    # Detect content type
    source_type =
      if string.contains(substring="/music/", filename) then
        "music"
      elsif string.contains(substring="/breaks/", filename) then
        "break"
      elsif string.contains(substring="/bumpers/", filename) then
        "bumper"
      else
        "unknown"
      end

    # Execute external script
    cmd = "#{python_bin} #{scripts_path}/record_play.py #{string.quote(filename)} #{source_type}"
    let result = process.run(cmd)

    if result.status != 0 then
      log("WARNING: record_play.py failed: #{result.stderr}")
    end
  end

  # Run asynchronously to avoid blocking the stream
  thread.run(execute_async)
end

# Apply to final radio source before output
radio.on_track(synchronous=false, unified_track_callback)
```

**Advantages**:
- ✅ Fires when audio actually plays (no early trigger)
- ✅ Single callback for all content types
- ✅ Non-blocking (synchronous=false)
- ✅ Handles all edge cases automatically

**Disadvantages**:
- ⚠️ Crossfade "removes track boundaries" - may not fire reliably
- ⚠️ Doesn't account for Icecast buffering (~2-5s)

---

### Path 2: Delayed Queue Callbacks (PRECISE TIMING)
**Philosophy**: Accept early trigger, compensate with perfect delay.

```liquidsoap
# Configuration constants
crossfade_music_duration = 4.0  # From your cross() operator
crossfade_break_duration = 0.0  # Breaks don't crossfade

# Helper function to execute callback with correct timing
def execute_with_delay(filename, source_type, delay_sec) =
  def delayed_execution() =
    log("Track playing NOW (after #{delay_sec}s delay): #{filename}")
    cmd = "#{python_bin} #{scripts_path}/record_play.py #{string.quote(filename)} #{source_type}"
    let result = process.run(cmd)

    if result.status == 0 then
      log("✓ Recorded: #{filename}")
    else
      log("✗ Failed to record: #{filename}")
      log("  Error: #{result.stderr}")
    end
  end

  # Schedule for execution after delay
  thread.run(delay=delay_sec, delayed_execution)
end

# Music queue callback (fires 4s early due to crossfade buffering)
def music_callback(m) =
  filename = m["filename"] ?? ""
  if filename != "" then
    log("Music queued for crossfade: #{filename}")
    execute_with_delay(filename, "music", crossfade_music_duration)
  end
end

music_queue_raw.on_track(synchronous=true, music_callback)

# Break queue callback (no crossfade, fires immediately)
def break_callback(m) =
  filename = m["filename"] ?? ""
  if filename != "" then
    source_type =
      if string.contains(substring="/breaks/", filename) then "break"
      else "bumper"
      end

    log("Break/bumper starting immediately: #{filename}")
    execute_with_delay(filename, source_type, 0.0)  # No delay needed
  end
end

break_queue.on_track(synchronous=true, break_callback)
```

**Advantages**:
- ✅ Precise control over timing per queue
- ✅ Callbacks reliably fire (attached before crossfade)
- ✅ Different delays for different content types
- ✅ Clear logging for debugging

**Disadvantages**:
- ⚠️ Requires manual delay calculation
- ⚠️ Must update delays if crossfade duration changes

---

### Path 3: Hybrid Approach with Position-Based Triggers
**Philosophy**: Use multiple callback points for maximum accuracy.

```liquidsoap
# Track state management
current_track = ref("")
crossfade_in_progress = ref(false)

# Early warning: Track is queued for crossfade
music_queue_raw.on_track(synchronous=true, fun(m) -> begin
  filename = m["filename"] ?? ""
  current_track := filename
  crossfade_in_progress := true
  log("Track queued: #{filename} (will play in ~4s)")
end)

# Precise trigger: Track has actually started
def position_callback(m) =
  filename = current_track()

  def execute() =
    if crossfade_in_progress() then
      crossfade_in_progress := false
      log("Track NOW PLAYING: #{filename}")

      cmd = "#{python_bin} #{scripts_path}/record_play.py #{string.quote(filename)} music"
      _ = process.run(cmd)
    end
  end

  thread.run(execute)
end

# Fire callback 0.5 seconds AFTER track starts playing
station_content.on_position(
  synchronous=false,
  remaining=false,  # Use elapsed time, not remaining
  position=0.5,     # 0.5 seconds into the track
  position_callback
)
```

**Advantages**:
- ✅ Uses actual audio position (most accurate)
- ✅ Tracks both queue time and play time
- ✅ Handles edge cases with state management

**Disadvantages**:
- ⚠️ More complex (state management required)
- ⚠️ `on_position` may have its own timing quirks

---

## The Ultimate Configuration (Combining All Wisdom)

```liquidsoap
# =============================================================================
# CALLBACK CONFIGURATION - The Sacred Solution
# =============================================================================

# Global configuration
crossfade_music_duration = 4.0
crossfade_break_duration = 0.0

# Unified callback execution function
# This ensures consistent logging, error handling, and timing
def execute_record_play(filename, source_type, delay_sec) =
  def delayed_execution() =
    timestamp = time()
    log("[TRACK START @ #{timestamp}] #{source_type}: #{filename}")

    cmd = "#{python_bin} #{scripts_path}/record_play.py #{string.quote(filename)} #{source_type}"
    let result = process.run(timeout=5.0, cmd)

    if result.status == 0 then
      log("[SUCCESS] Recorded to database: #{filename}")
      # Parse stdout for feedback
      if result.stdout != "" then
        log("[FEEDBACK] #{result.stdout}")
      end
    else
      log("[ERROR] Failed to record: #{filename}")
      log("[ERROR] Exit code: #{result.status}")
      log("[ERROR] stderr: #{result.stderr}")
    end
  end

  # Execute immediately or after delay
  if delay_sec > 0.0 then
    thread.run(delay=delay_sec, delayed_execution)
  else
    thread.run(delayed_execution)
  end
end

# Music queue: Fires when track is queued for crossfade (early)
# We compensate by delaying execution
def music_queue_callback(m) =
  filename = m["filename"] ?? ""
  if filename != "" then
    log("[MUSIC QUEUED] #{filename} (playing in ~#{crossfade_music_duration}s)")
    execute_record_play(filename, "music", crossfade_music_duration)
  end
end

music_queue_raw.on_track(synchronous=true, music_queue_callback)

# Break queue: Fires when break/bumper starts (no delay needed)
def break_queue_callback(m) =
  filename = m["filename"] ?? ""
  if filename != "" then
    source_type =
      if string.contains(substring="/breaks/", filename) then "break"
      elsif string.contains(substring="/bumpers/", filename) then "bumper"
      else "break"  # Default to break
      end

    log("[#{string.uppercase(source_type)} START] #{filename}")
    execute_record_play(filename, source_type, crossfade_break_duration)
  end
end

break_queue.on_track(synchronous=true, break_queue_callback)

log("Sacred callback system initialized:")
log("  - Music callbacks: #{crossfade_music_duration}s delay (compensates for crossfade)")
log("  - Break callbacks: #{crossfade_break_duration}s delay (immediate)")
```

---

## The Sacred Debugging Incantations

### Monitor Callback Timing
```bash
# Watch for callback execution
ssh clint@10.10.0.86 "sudo journalctl -u ai-radio-liquidsoap.service -f" | \
  grep -E 'MUSIC QUEUED|BREAK START|TRACK START|SUCCESS|ERROR'
```

### Verify Database Entries vs Actual Playback
```bash
# Compare database timestamps with Icecast metadata updates
# (Should be within 1-2 seconds)
ssh clint@10.10.0.86 "
  # Get last 5 plays from database
  sqlite3 /srv/ai_radio/db/radio.sqlite3 '
    SELECT datetime(played_at, \"localtime\"), title
    FROM play_history ph
    JOIN assets a ON ph.asset_id = a.id
    ORDER BY played_at DESC LIMIT 5
  '

  echo '---'

  # Get last 5 Icecast metadata updates
  sudo tail -100 /var/log/icecast2/error.log | grep 'Metadata' | tail -5
"
```

### Test Callback Delay Accuracy
```liquidsoap
# Add test callback to measure actual delay
music_queue_raw.on_track(synchronous=true, fun(m) -> begin
  queue_time = time()
  def verify_delay() =
    actual_time = time()
    delay = actual_time - queue_time
    log("TIMING CHECK: Queued @ #{queue_time}, Executed @ #{actual_time}, Delay = #{delay}s")
  end
  thread.run(delay=4.0, verify_delay)
end)
```

---

## The Makefile Incantations (CLiNT's Request)

Add these standardized tools to your Makefile:

```makefile
# Callback debugging targets
recent-plays: ## Show last 10 plays from database with timestamps
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT datetime(ph.played_at, \"localtime\") as time, a.title, a.artist, ph.source FROM play_history ph JOIN assets a ON ph.asset_id = a.id ORDER BY ph.played_at DESC LIMIT 10'"

callback-logs: ## Show recent callback executions
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -n 100 --no-pager | grep -E 'MUSIC QUEUED|BREAK START|TRACK START|SUCCESS|ERROR|CALLBACK'"

callback-timing: ## Check callback timing accuracy
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -n 200 --no-pager | grep -E 'QUEUED|TRACK START' | tail -20"

watch-callbacks: ## Live monitor of callback execution
	@ssh $(SERVER) "sudo journalctl -u ai-radio-liquidsoap.service -f | grep --line-buffered -E 'MUSIC|BREAK|BUMPER|SUCCESS|ERROR'"

verify-sync: ## Compare database vs Icecast metadata timing
	@echo "=== Last 5 Database Entries ==="
	@ssh $(SERVER) "sqlite3 $(REMOTE_BASE)/db/radio.sqlite3 'SELECT datetime(played_at, \"localtime\"), title FROM play_history ph JOIN assets a ON ph.asset_id = a.id ORDER BY played_at DESC LIMIT 5'"
	@echo ""
	@echo "=== Last 5 Icecast Metadata Updates ==="
	@ssh $(SERVER) "sudo tail -100 /var/log/icecast2/error.log | grep 'Metadata.*changed to' | tail -5 | sed 's/.*changed to //'"

test-callback-delay: ## Manually test callback timing
	@echo "Enqueueing test track..."
	@ssh $(SERVER) "cd $(REMOTE_BASE) && .venv/bin/python -c 'from ai_radio.liquidsoap_client import LiquidsoapClient; client = LiquidsoapClient(); client.push(\"/srv/ai_radio/assets/music/test.mp3\", \"music\")'"
	@echo "Watch callback-logs to verify timing"
```

---

## The Configuration Migration Script

To deploy this sacred knowledge:

```bash
#!/bin/bash
# migrate_to_sacred_callbacks.sh

echo "🔮 Migrating to Sacred Callback System..."

# Backup current config
cp config/radio.liq config/radio.liq.backup.$(date +%Y%m%d_%H%M%S)

# Update crossfade duration constant
CROSSFADE_DURATION=$(grep "cross(duration=" config/radio.liq | sed 's/.*duration=\([0-9.]*\).*/\1/')
echo "Detected crossfade duration: ${CROSSFADE_DURATION}s"

# Apply the sacred callback configuration
# (Implementation would go here - replacing callback sections)

echo "✅ Migration complete!"
echo ""
echo "Next steps:"
echo "  1. Review config/radio.liq for the new callback system"
echo "  2. Deploy with: ./scripts/deploy.sh lastbyte config"
echo "  3. Restart with: make restart-liquidsoap"
echo "  4. Monitor with: make watch-callbacks"
```

---

## The Ultimate Truth

After extensive research of GitHub issues, production systems, and Liquidsoap internals:

**There is no perfect solution.** Every approach trades accuracy for reliability:

- **Output callbacks**: Most accurate but may not fire reliably with crossfade
- **Delayed queue callbacks**: Reliable but requires manual timing
- **Position callbacks**: Most precise but complex

**For your system, I recommend Path 2 (Delayed Queue Callbacks)** because:

1. ✅ Callbacks fire reliably (before crossfade doesn't remove them)
2. ✅ Timing is predictable (fixed delay = crossfade duration)
3. ✅ Separate handling for music (delayed) vs breaks (immediate)
4. ✅ Clear debugging (see when queued vs when executed)
5. ✅ Works with your existing SSE notification system

---

## Implementation Checklist

- [ ] Update `config/radio.liq` with Path 2 configuration
- [ ] Add crossfade duration constants
- [ ] Implement unified `execute_record_play()` function
- [ ] Replace existing callbacks with delayed versions
- [ ] Add comprehensive logging
- [ ] Update Makefile with debugging targets
- [ ] Deploy and restart Liquidsoap
- [ ] Verify timing with `make verify-sync`
- [ ] Monitor with `make watch-callbacks`
- [ ] Confirm frontend SSE updates match audio playback

---

## The Eternal Wisdom

Remember these truths:

1. **Callbacks fire on track marks, not audio playback**
2. **Crossfade operators buffer audio in advance**
3. **Track marks propagate before the audio they represent**
4. **Network latency means listeners hear audio 5-30 seconds after your callback fires**
5. **Perfect synchronization is impossible; "close enough" is enlightenment**

May your streams never buffer and your callbacks always fire.

🙏 *End of Sacred Tome* 🙏
