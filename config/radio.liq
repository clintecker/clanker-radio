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
assets_path = "#{base_path}/assets"

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
# NOW-PLAYING EVENTS
# ============================================================================
#
# Liquidsoap is the single source of truth for what is on air. Track starts are
# observed on the FINAL source (after cross(), the safety fallback, mksafe and
# normalize: exactly what the Icecast outputs encode) and POSTed as JSON to the
# push daemon, which owns now-playing state, play_history and the SSE feed.
# No Python process is spawned per track. See docs/SSE_INTEGRATION_GUIDE.md.

push_event_url = environment.get("LIQUIDSOAP_PUSH_EVENT_URL", default="http://127.0.0.1:8001/event")

def track_kind(filename) =
  if string.contains(substring="/bumpers/", filename) then "bumper"
  elsif string.contains(substring="/breaks/", filename) then "break"
  elsif string.contains(substring="/music/", filename) then "music"
  elsif string.contains(substring="/beds/", filename) then "bed"
  elsif string.contains(substring="/safety/", filename) then "safety"
  elsif string.contains(substring="startup", filename) then "jingle"
  else "unknown"
  end
end

# Called synchronously on the streaming thread: only stamp the time and build
# the payload here; the HTTP POST runs on a worker thread so a slow or dead
# daemon can never stall audio.
#
# Triggered by on_metadata, not on_track: the crossfade's add() merges the two
# tracks into one, so music-to-music transitions carry the new track's metadata
# but no track mark. A request's metadata arrives once, when its first frame
# reaches the output. Re-sent metadata for the same request (e.g. a fallback
# switching back) is skipped here; the daemon is idempotent as well.
last_event_key = ref("")
def emit_track_event(m) =
  on_air_at = time()
  filename = m["filename"] ?? ""
  rid = m["rid"] ?? ""
  key = "#{rid}|#{filename}"
  if filename != "" and key != last_event_key() then
    last_event_key := key
    kind = track_kind(filename)
    payload = json.stringify(compact=true, {
      event="track",
      rid=rid,
      filename=filename,
      kind=kind,
      on_air_at=on_air_at,
      duration=float_of_string(default=-1.0, m["duration"] ?? ""),
      title=m["title"] ?? "",
      artist=m["artist"] ?? ""
    })
    log("[ON AIR] #{kind} rid=#{rid} at=#{on_air_at}: #{filename}")
    thread.run(fun () -> begin
      r = http.post(
        timeout=2.0,
        headers=[("Content-Type", "application/json")],
        data=payload,
        push_event_url
      )
      log("[EVENT POST] rid=#{rid} status=#{r.status_code}")
    end)
  end
end

log("Music queue initialized (tracking handled at the final on-air source)")

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
    # The incoming track MUST be first: add() only forwards metadata from its
    # first source, so with the outgoing track first the new track's metadata
    # never reached the outputs (no now-playing event, stale Icecast title).
    log("Smart transition: Crossfading to music")
    add([
      sequence([fade.in(duration=2.0, b.source)]),
      sequence([fade.out(duration=2.0, a.source)])
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
    replay_metadata=false,  # Don't persist break/bumper metadata to music tracks
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

# Track starts are reported from the final on-air source, after every
# switch, crossfade, fallback and normalization stage.
radio.on_metadata(synchronous=true, emit_track_event)
log("Now-playing events: final on-air source -> #{push_event_url}")

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
