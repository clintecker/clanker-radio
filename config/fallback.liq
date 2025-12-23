#!/usr/bin/env liquidsoap
# ============================================================================
# FALLBACK MOUNT - Technical Difficulties Loop
# ============================================================================
#
# This simple Liquidsoap instance feeds /radio-fallback mount on Icecast
# Plays when main /radio mount disconnects (Liquidsoap restart/maintenance)
# Listeners are seamlessly redirected between mounts by Icecast

# =============================================================================
# Path Configuration
# =============================================================================

base_path = environment.get("LIQUIDSOAP_BASE_PATH", default="/srv/ai_radio")
assets_path = "#{base_path}/assets"

# =============================================================================
# Logging Configuration
# =============================================================================

log.level.set(3)
log.file.set(true)
log.file.path.set("#{base_path}/logs/liquidsoap-fallback.log")

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

station_name = environment.get("LIQUIDSOAP_STATION_NAME", default="WKRP Coconut Island")
station_description = "Technical Difficulties - Back Shortly"
station_genre = "Broadcast Interruption"
station_url = environment.get("LIQUIDSOAP_STATION_URL", default="http://your-station-url.com")

# =============================================================================
# Fallback Source - Rotate through technical difficulties tracks
# =============================================================================

# Playlist of technical difficulties tracks - plays randomly
fallback_source = playlist(
    id="technical_difficulties",
    mode="randomize",
    reload=3600,
    "#{assets_path}/technical_difficulties/"
)

# Make source infallible and normalize volume
fallback_source = mksafe(fallback_source)
fallback_source = normalize(
    target=-16.0,
    threshold=-40.0,
    gain_min=-6.0,
    gain_max=6.0,
    fallback_source
)

log("Fallback source configured: looping technical difficulties track")

# =============================================================================
# Icecast Output - /radio-fallback mount
# =============================================================================

output.icecast(
  %mp3(bitrate=192, samplerate=48000, stereo=true),
  host=icecast_host,
  port=icecast_port,
  password=icecast_password(),
  mount="/radio-fallback",
  name=station_name,
  description=station_description,
  genre=station_genre,
  url=station_url,
  fallback_source
)

log("Fallback mount streaming to /radio-fallback on Icecast")
