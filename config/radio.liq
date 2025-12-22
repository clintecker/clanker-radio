#!/usr/bin/env liquidsoap
# ============================================================================
# UNIX SOCKET INTERFACE (Phase 3)
# ============================================================================

settings.server.socket := true
settings.server.socket.path := "/run/liquidsoap/radio.sock"
settings.server.socket.permissions := 0o660

log("Unix socket enabled: /run/liquidsoap/radio.sock")

# AI Radio Station - Liquidsoap Configuration

# =============================================================================
# Logging Configuration
# =============================================================================

log.level.set(3)
log.file.set(true)
log.file.path.set("/srv/ai_radio/logs/liquidsoap.log")

# =============================================================================
# Icecast Configuration  
# =============================================================================

icecast_password_file = "/srv/ai_radio/.icecast_secrets"
def icecast_password() =
  list.hd(default="", file.lines(icecast_password_file))
end

icecast_host = "127.0.0.1"
icecast_port = 8000

# =============================================================================
# Station Metadata
# =============================================================================

station_name = "LAST BYTE RADIO"
station_description = "Broadcasting from the neon-lit wasteland of Chicago"
station_genre = "Various"
station_url = "https://radio.clintecker.com"

# ============================================================================
# QUEUE SOURCES
# ============================================================================

# Level 1: Operator override queue (buffered for instant switching)
override_queue = buffer(request.queue(id="override"))
log("Override queue initialized with buffer (Level 1)")

# Level 2: Break queue (no buffer to prevent interrupting during crossfades)
break_queue = request.queue(id="breaks")
log("Break queue initialized (Level 2)")

# Level 3: Music queue - Apply crossfade HERE before fallback
music_queue_raw = request.queue(id="music")

# Helper function to record plays
def record_play_callback(m) =
    filename = m["filename"] ?? ""
    log("CALLBACK FIRED: #{filename}")
    if filename != "" then
        source_type = "music"
        cmd = "/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/record_play.py #{string.quote(filename)} #{source_type}"
        log("Executing: #{cmd}")
        # Use system() for fire-and-forget instead of process.run()
        ignore(system(cmd))
        log("Callback completed for #{filename}")
    end
end

# Attach callback to raw queue BEFORE crossfade (async to prevent audio thread blocking)
music_queue_raw.on_track(synchronous=false, record_play_callback)

# Apply crossfade with proper overlap to prevent gaps/volume dips
music_queue = crossfade(
    duration=4.0,           # 4 second window for safe overlap
    fade_in=2.0,            # 2 second fade in
    fade_out=2.0,           # 2 second fade out (ensures 2s overlap)
    music_queue_raw
)
log("Music queue initialized with play tracking and 2s crossfade (Level 3)")

# ============================================================================
# BREAK QUEUE SETUP
# ============================================================================
# Breaks and station IDs are queued directly to break_queue by:
# - generate_break.py (top of hour news breaks)
# - schedule_station_id.py (station IDs at :15, :30, :45)
# The fallback chain's track_sensitive=true ensures they wait for track boundaries

log("Break queue configured for direct fallback access")

# ============================================================================
# BED PLAYLIST
# ============================================================================

beds = playlist(
    id="beds",
    mode="random",
    reload=3600,
    "/srv/ai_radio/assets/beds"
)
log("Bed playlist configured (level 4 fallback)")


# ============================================================================
# SAFETY SOURCES
# ============================================================================

emergency_tone = single("/srv/ai_radio/assets/safety/safety_tone.wav")

safety_playlist = playlist(
  mode="randomize",
  reload=3600,
  "/srv/ai_radio/assets/safety/evergreen.m3u"
)

# ============================================================================
# STARTUP JINGLE - Plays once on startup (18s, looped voice)
# Gives time for: stream to establish, music to enqueue, listeners to reconnect
# ============================================================================

startup_jingle = single(
    id="startup",
    "/srv/ai_radio/assets/startup.mp3"
)
log("Startup jingle configured (18 seconds, looped voice)")

# ============================================================================
# MAIN SWITCHING LOGIC - Breaks interrupt at track boundaries
# ============================================================================

# CRITICAL: Use switch instead of fallback to allow breaks to interrupt music
# switch checks conditions top-to-bottom and plays the first match
# track_sensitive on switch means "wait for track boundary before switching"

station_content = switch(
    id="main_switch",
    track_sensitive=true,  # Waits for current track to finish before switching
    [
        # Level 1: Operator override (always highest priority)
        # source.is_ready checks if source has content ready to play
        ({source.is_ready(override_queue)}, override_queue),

        # Level 2: Breaks & station IDs (interrupt music when present)
        ({source.is_ready(break_queue)}, break_queue),

        # Level 3: Music (default content)
        ({source.is_ready(music_queue)}, music_queue)
    ]
)

# Safety fallback in case everything above fails
station_content = fallback(
    track_sensitive=false,  # Immediately switch to safety if needed
    [
        station_content,
        beds,
        safety_playlist,
        emergency_tone
    ]
)

log("Interrupt-based switching configured: overrides and breaks interrupt music at track boundaries")

# ============================================================================
# SEQUENCE - Play startup jingle ONCE, then switch to station content forever
# ============================================================================

# This solves the startup race condition:
# - Startup jingle plays immediately (8 seconds)
# - Music enqueues while jingle is playing
# - After jingle finishes, sequence switches to station_content
# - Music is ready and plays immediately
# Result: Zero dead air, no long bed tracks on startup
radio_raw = sequence([
    startup_jingle,      # Plays once
    station_content      # Plays forever after jingle
])

# Make source infallible before normalize
radio = mksafe(radio_raw)

log("Startup sequence configured: jingle -> station content")

# =============================================================================
# Audio Processing
# =============================================================================

# Gentle normalization to even out volume levels without artifacts
radio = normalize(
  target=-16.0,         # Slightly louder target (less aggressive)
  threshold=-40.0,      # Noise gate threshold
  gain_min=-6.0,        # Limit boost to prevent distortion
  gain_max=6.0,         # Limit cut to maintain dynamics
  radio
)
log("Volume normalization enabled (gentle settings)")

# =============================================================================
# Play Tracking
# =============================================================================

# Track breaks, bumpers, and beds at the main output level
# (Music is tracked on the queue before crossfading, async to prevent blocking)
radio.on_track(synchronous=false, fun(m) -> begin
    filename = m["filename"] ?? ""

    if filename != "" then
        # Track different content types based on path
        if string.contains(substring="/breaks/", filename) then
            log("BREAK CALLBACK: #{filename}")
            cmd = "/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/record_play.py #{string.quote(filename)} break"
            log("Executing: #{cmd}")
            ignore(system(cmd))
            log("Break callback completed")
        elsif string.contains(substring="/bumpers/", filename) then
            log("BUMPER CALLBACK: #{filename}")
            cmd = "/srv/ai_radio/.venv/bin/python /srv/ai_radio/scripts/record_play.py #{string.quote(filename)} bumper"
            log("Executing: #{cmd}")
            ignore(system(cmd))
            log("Bumper callback completed")
        elsif string.contains(substring="/beds/", filename) then
            # Beds aren't in database, just log
            log("Bed playing: #{filename}")
        end
    end
end)

log("Play tracking enabled for breaks, bumpers, and beds")

# =============================================================================
# Icecast Output
# =============================================================================

output.icecast(
  %mp3(bitrate=192, samplerate=48000, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/radio",
  name=station_name,
  description=station_description,
  genre=station_genre,
  url=station_url,
  radio
)
