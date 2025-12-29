# Clanker Radio - Project Context

## Server Connection

**Production Server IP:** `10.10.0.86`
**User:** `clint`
**Connection:** `ssh clint@10.10.0.86`

All deployment and remote operations use this IP address. The server is only accessible via local network.

## Common Operations

See `Makefile` for standardized commands for:
- Deploying code/scripts/frontend
- Checking service status
- Viewing logs
- Monitoring Liquidsoap
- Testing SSE notifications

**Important:** If you find yourself running the same non-`make` commands more than a couple times, create a new Makefile target for it. This codifies common operations and prevents errors from retyping commands.

## Architecture

### Real-time Updates (SSE)
- **SSE Daemon:** `push_daemon.py` on port 8001
- **Notification Flow:** Liquidsoap callback → record_play.py → export_now_playing.py → HTTP POST to localhost:8001/notify
- **Frontend:** EventSource connection to `/api/stream`
- **Complete State:** Every SSE push delivers full JSON: current track, next track, history (5 tracks), stream stats

### Services
- `ai-radio-liquidsoap.service` - Main audio streaming
- `ai-radio-push.service` - SSE daemon for real-time frontend updates
- `ai-radio-break-gen.service` - News break generation (timer-triggered)
- `ai-radio-station-id.service` - Station ID enqueue (timer-triggered)
- `ai-radio-enqueue.service` - Track enqueuing (timer-triggered)

### Database
- **Location:** `/srv/ai_radio/db/radio.sqlite3`
- **Owner:** `ai-radio:ai-radio`
- **Tables:** assets, play_history, queue, etc.

## Debugging

### Check if callbacks are firing
```bash
make logs-liquidsoap
# Look for "CALLBACK FIRED" and "Process stdout"
```

### Check SSE daemon
```bash
make logs-push
# Look for "Broadcasting update to N clients"
```

### Check export script
```bash
make check-exports
# Shows recent export logs
```

### Manual SSE notification test
```bash
make test-sse
```

## Configuration Refactor (2025-12-28)

Config system was refactored from flat structure to domain-based Pydantic models:
- `config.paths.*` - File paths
- `config.tts.*` - Text-to-speech settings
- `config.announcer.*` - Personality/voice settings
- `config.content.*` - Content generation (hallucinations, etc.)
- `config.db.*` - Database settings

Deprecated property shims in `config/base.py` provide backward compatibility for legacy code.
