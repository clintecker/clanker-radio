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
# Path Configuration (from environment)
# =============================================================================

base_path = environment.get("LIQUIDSOAP_BASE_PATH", default="/srv/ai_radio")
python_bin = "#{base_path}/.venv/bin/python"
assets_path = "#{base_path}/assets"
scripts_path = "#{base_path}/scripts"

# =============================================================================
# Logging Configuration
# =============================================================================

log.level.set(3)
log.file.set(true)
log.file.path.set("#{base_path}/logs/liquidsoap.log")

# =============================================================================
# Icecast Configuration
# =============================================================================

icecast_password_file = "#{base_path}/.icecast_secrets"
def icecast_password() =
  list.hd(default="", file.lines(icecast_password_file))
end

icecast_host = "127.0.0.1"
icecast_port = 8000

# =============================================================================
# Station Metadata
# =============================================================================
# Override these values with environment variables or edit directly:
# - LIQUIDSOAP_STATION_NAME
# - LIQUIDSOAP_STATION_DESCRIPTION
# - LIQUIDSOAP_STATION_URL

station_name = environment.get("LIQUIDSOAP_STATION_NAME", default="WKRP Coconut Island")
station_description = environment.get("LIQUIDSOAP_STATION_DESCRIPTION", default="Broadcasting from paradise - island vibes and good times")
station_genre = "Tropical / Variety"
station_url = environment.get("LIQUIDSOAP_STATION_URL", default="http://your-station-url.com")

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

# ============================================================================
# CALLBACK CONFIGURATION - Compensates for crossfade timing
# ============================================================================
#
# IMPORTANT: Music callbacks fire when track is QUEUED for crossfade, not when
# it actually plays. The cross() operator buffers audio 4 seconds in advance.
# Solution: Delay callback execution to match actual playback time.
#
# See docs/LIQUIDSOAP_SACRED_TOME.md for full documentation.

# Crossfade duration (must match cross() operator below)
crossfade_music_duration = 4.0
crossfade_break_duration = 0.0

# Unified callback execution with delay compensation
def execute_record_play(filename, source_type, delay_sec) =
  def delayed_execution() =
    log("[TRACK START] #{source_type}: #{filename}")

    cmd = "#{python_bin} #{scripts_path}/record_play.py #{string.quote(filename)} #{source_type}"
    _ = process.run(cmd)

    log("[CALLBACK] Executed record_play for #{filename}")
  end

  # Execute immediately or after delay
  if delay_sec > 0.0 then
    thread.run(delay=delay_sec, delayed_execution)
  else
    thread.run(delayed_execution)
  end
end

# Music queue callback - fires 4s early, compensate with delay
def music_callback(m) =
  filename = m["filename"] ?? ""
  if filename != "" then
    log("[MUSIC QUEUED] #{filename} (playing in ~#{crossfade_music_duration}s)")
    execute_record_play(filename, "music", crossfade_music_duration)
  end
end

music_queue_raw.on_track(synchronous=true, music_callback)
log("Music queue initialized with delayed callback (compensates for 4s crossfade buffer)")

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
    "#{assets_path}/beds"
)
log("Bed playlist configured (level 4 fallback)")


# ============================================================================
# SAFETY SOURCES
# ============================================================================

emergency_tone = single("#{assets_path}/safety/safety_tone.wav")

safety_playlist = playlist(
  mode="randomize",
  reload=3600,
  "#{assets_path}/safety/evergreen.m3u"
)

# ============================================================================
# STARTUP JINGLE - Plays once on startup (18s, looped voice)
# Gives time for: stream to establish, music to enqueue, listeners to reconnect
# ============================================================================

startup_jingle = single(
    id="startup",
    "#{assets_path}/startup.mp3"
)
log("Startup jingle configured (18 seconds, looped voice)")

# ============================================================================
# SMART TRANSITION FUNCTION - Break-aware crossfading
# ============================================================================

# Custom transition function that inspects metadata to decide fade vs cut
# Called by cross() operator at every track boundary
# Receives: a (ending track), b (starting track) with .metadata and .source

def smart_transition(a, b) =
  # Get filename from incoming track metadata
  next_file = b.metadata["filename"] ?? ""

  # Check if next track is a break or station ID
  is_break = string.contains(substring="/breaks/", next_file) or
             string.contains(substring="/bumpers/", next_file)

  if is_break then
    # Hard cut for breaks - no overlap
    log("Smart transition: Hard cut to break/bumper")
    sequence([a.source, b.source])
  else
    # Smooth crossfade for music (4 seconds total: 2s fade-out + 2s fade-in)
    log("Smart transition: Crossfading to music")
    add([
      sequence([fade.out(duration=2.0, a.source)]),
      sequence([fade.in(duration=2.0, b.source)])
    ])
  end
end

log("Smart transition function defined (break-aware crossfading)")

# ============================================================================
# MAIN SWITCHING LOGIC - Breaks interrupt at track boundaries
# ============================================================================

# CRITICAL: Use switch instead of fallback to allow breaks to interrupt music
# switch checks conditions top-to-bottom and plays the first match
# track_sensitive on switch means "wait for track boundary before switching"

station_content_raw = switch(
    id="main_switch",
    track_sensitive=true,  # Waits for current track to finish before switching
    [
        # Level 1: Operator override (always highest priority)
        # source.is_ready checks if source has content ready to play
        ({source.is_ready(override_queue)}, override_queue),

        # Level 2: Breaks & station IDs (interrupt music when present)
        ({source.is_ready(break_queue)}, break_queue),

        # Level 3: Music (default content) - using raw queue
        ({source.is_ready(music_queue_raw)}, music_queue_raw)
    ]
)

log("Switch configured: overrides and breaks interrupt music at track boundaries")

# Apply smart transition using cross() operator
# Duration should accommodate the longest transition (4 seconds)
station_content = cross(duration=4.0, smart_transition, station_content_raw)

log("Smart transitions applied: music crossfades smoothly, breaks cut cleanly")

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

log("Safety fallback configured (beds → safety playlist → emergency tone)")

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
# (Music is tracked on the queue before crossfading)
# Breaks/bumpers play immediately (no crossfade), so no delay needed
radio.on_track(synchronous=true, fun(m) -> begin
    filename = m["filename"] ?? ""

    if filename != "" then
        # Track different content types based on path
        if string.contains(substring="/breaks/", filename) then
            log("[BREAK START] #{filename}")
            execute_record_play(filename, "break", crossfade_break_duration)
        elsif string.contains(substring="/bumpers/", filename) then
            log("[BUMPER START] #{filename}")
            execute_record_play(filename, "bumper", crossfade_break_duration)
        elsif string.contains(substring="/beds/", filename) then
            # Beds aren't in database, just log
            log("Bed playing: #{filename}")
        end
    end
end)

log("Play tracking enabled for breaks, bumpers, and beds")

# =============================================================================
# Icecast Output - Multiple Bitrates
# =============================================================================

# High quality stream (192kbps) - Main mount
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

# Medium quality stream (128kbps) - Balanced quality/bandwidth
output.icecast(
  %mp3(bitrate=128, samplerate=44100, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/radio-128",
  name="#{station_name} (128kbps)",
  description=station_description,
  genre=station_genre,
  url=station_url,
  radio
)

# Low bandwidth stream (96kbps) - Mobile/slow connections
output.icecast(
  %mp3(bitrate=96, samplerate=44100, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/radio-96",
  name="#{station_name} (96kbps)",
  description=station_description,
  genre=station_genre,
  url=station_url,
  radio
)
