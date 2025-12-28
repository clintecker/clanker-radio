# DJ Tag Generator - Design Document

**Date:** 2025-12-28
**Status:** Ready for Implementation
**Author:** CLiNT + Claude

---

## Overview

Build a web-based DJ tag generator as an admin utility. Users input text, select voice parameters, and download generated audio tags for DJ mixes. This tool reuses existing Gemini TTS infrastructure but provides simplified, configurable voice synthesis separate from radio station broadcasts.

## Requirements

### Functional
- Web UI for text input and parameter configuration
- Real-time progress updates during 20-120 second generation
- Automatic MP3 download when complete
- Access restricted to admin users (HTTP Basic Auth)
- Support all 30+ Gemini TTS voice options
- Configurable parameters: temperature, speaking rate, pitch, style prompt
- Model selection (Flash vs Pro)

### Non-Functional
- Handle 20-120 second generation times without timeout
- Work across all modern browsers
- Reuse existing Gemini API credentials
- No permanent storage (24-hour cleanup)
- Single user tool (no queue management needed)

## Architecture

### Components

**Frontend** (`nginx/admin/dj_tag.html`)
- Form with controls for all Gemini TTS parameters
- JavaScript handles API calls and SSE progress streaming
- Auto-downloads MP3 when generation completes
- Cyberpunk-styled UI matching existing admin pages

**Backend API** (`scripts/api_dj_tag.py`)
- Flask application on port 5001
- Two endpoints:
  - `POST /api/dj-tag/generate` - Start generation, return job_id
  - `GET /api/dj-tag/stream/<job_id>` - SSE progress stream
- Returns generated MP3 for download

**Core Logic** (`src/ai_radio/dj_tag_generator.py`)
- Simplified Gemini TTS wrapper
- No five-element framework (unlike radio station voice)
- Direct text-to-speech with configurable parameters
- Progress callbacks for SSE streaming
- Reuses existing PCM-to-MP3 conversion (ffmpeg)

**Nginx Proxy**
- HTTP Basic Auth on all endpoints (reuses `/etc/nginx/.htpasswd`)
- Proxies `/api/dj-tag/*` to Flask on 127.0.0.1:5001
- SSE-optimized headers (buffering off, long timeouts)

**Storage**
- Temporary directory: `/srv/ai_radio/tmp/dj_tags/`
- Auto-cleanup after 24 hours
- Max 100 files (~50MB total)

## Data Flow

```
1. User visits /admin/dj-tag.html (auth required)
2. User enters text and selects parameters
3. Frontend: POST /api/dj-tag/generate
4. Backend: Returns {job_id, stream_url}
5. Frontend: Opens EventSource to stream_url
6. Backend: Streams SSE progress events
   - event: progress, data: {"percent": 30, "message": "Generating audio..."}
7. Backend: Completes generation
   - event: complete, data: {"download_url": "/api/dj-tag/download/abc123.mp3"}
8. Frontend: Auto-downloads MP3
```

## API Specification

### POST /api/dj-tag/generate

**Request:**
```json
{
  "text": "oh, holy shit! They put MISTER BEEF in the booth?!?",
  "voice": "Laomedeia",
  "model": "gemini-2.5-pro-preview-tts",
  "temperature": 2.0,
  "speaking_rate": 1.0,
  "pitch": 0.0,
  "style_prompt": "excited and energetic"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "stream_url": "/api/dj-tag/stream/abc123"
}
```

### GET /api/dj-tag/stream/<job_id>

**SSE Events:**

Progress update:
```
event: progress
data: {"percent": 45, "message": "Converting PCM to MP3..."}
```

Completion:
```
event: complete
data: {"download_url": "/api/dj-tag/download/abc123.mp3", "filename": "dj_tag_abc123.mp3"}
```

Error:
```
event: error
data: {"error": "Gemini API quota exceeded", "retry": false}
```

## UI Controls

**Form Fields:**
- **Text Input** (textarea, required) - Tag text
- **Voice** (dropdown) - 30+ options (Kore, Puck, Laomedeia, etc.)
- **Model** (radio buttons) - Pro (quality) vs Flash (speed)
- **Temperature** (slider, 0.0-2.0, default 2.0) - Creativity
- **Speaking Rate** (slider, 0.5-2.0, default 1.0) - Speed
- **Pitch** (slider, -20 to +20, default 0.0) - Voice pitch
- **Style Prompt** (text input, optional) - Natural language style guide

**Progress Display:**
- Animated progress bar (0-100%)
- Status message updates in real-time
- Disable form during generation

## Error Handling

### Backend Errors

| Error | Retry? | Frontend Action |
|-------|--------|-----------------|
| Gemini quota exceeded | No | Show error, no retry button |
| Gemini timeout (120s) | Yes | Show error with retry button |
| FFmpeg conversion failed | Yes | Show error with retry button |
| Invalid input (empty/too long) | No | Show validation error |
| Disk space full | No | Show error, contact admin |

### Frontend Errors

**Network-level errors** (connection drops):
- Show "Connection lost" with retry button
- Close EventSource gracefully

**Browser timeout** (fetch abort):
- 180 second timeout with AbortController
- Show timeout error with retry option

## Security

**Authentication:**
- All endpoints require HTTP Basic Auth
- Reuses existing `/etc/nginx/.htpasswd`
- Same credentials as other admin sections

**Access Control:**
- Flask binds to 127.0.0.1 only (no external access)
- All requests proxied through nginx
- Auth checked at nginx layer

**Resource Limits:**
- Max text length: 5000 characters
- Max file storage: 100 files
- Auto-cleanup after 24 hours

## Infrastructure Configuration

### Nginx Config

```nginx
upstream dj_tag_api {
    server 127.0.0.1:5001;
}

location /admin/dj-tag.html {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
    alias /srv/ai_radio/public/admin/dj_tag.html;
}

location /api/dj-tag/ {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 180s;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_pass http://dj_tag_api/;
}
```

### Systemd Service

```ini
[Unit]
Description=AI Radio DJ Tag Generator API
After=network.target

[Service]
Type=simple
User=clint
WorkingDirectory=/srv/ai_radio
Environment="PATH=/srv/ai_radio/.venv/bin"
ExecStart=/srv/ai_radio/.venv/bin/python scripts/api_dj_tag.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Timeouts

- Nginx `proxy_read_timeout`: 180s
- Flask request timeout: 180s
- Browser fetch timeout: 180s (via AbortController)
- Gemini generation max: 120s (abort after this)

## Testing Plan

### Manual Testing
- [ ] Auth required for /admin/dj-tag.html
- [ ] All 30 voices generate successfully
- [ ] Temperature 0.0, 1.0, 2.0 produce different results
- [ ] Speaking rate 0.5, 1.0, 2.0 work correctly
- [ ] Pitch -10, 0, +10 work correctly
- [ ] Style prompt affects output
- [ ] Progress bar updates in real-time
- [ ] MP3 auto-downloads when complete
- [ ] Empty text shows validation error
- [ ] Kill Flask mid-generation shows error + retry
- [ ] Multiple rapid generations all complete
- [ ] Old tags cleaned up after 24 hours

### API Testing
- [ ] POST without auth returns 401
- [ ] POST with empty text returns 400
- [ ] POST with valid text returns job_id
- [ ] SSE stream shows progress 0% → 100%
- [ ] SSE complete event includes download_url
- [ ] Downloaded MP3 plays correctly

## Deployment Steps

1. Create worktree: `git worktree add .worktrees/dj-tag-generator -b feature/dj-tag-generator`
2. Implement components (see implementation plan)
3. Deploy code: `./scripts/deploy.sh code`
4. Install systemd service:
   ```bash
   sudo cp systemd/ai-radio-dj-tag-api.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable ai-radio-dj-tag-api
   sudo systemctl start ai-radio-dj-tag-api
   ```
5. Update nginx config (add sections above)
6. Test nginx: `sudo nginx -t`
7. Reload nginx: `sudo systemctl reload nginx`
8. Deploy frontend: `./scripts/deploy.sh frontend`
9. Test end-to-end

## Monitoring

```bash
# Check API service
sudo systemctl status ai-radio-dj-tag-api

# Watch logs
sudo journalctl -u ai-radio-dj-tag-api -f

# Check nginx proxy
sudo tail -f /var/log/nginx/access.log | grep dj-tag

# Monitor disk usage
du -sh /srv/ai_radio/tmp/dj_tags/
```

## Success Criteria

- User can generate DJ tags with custom text
- All voice options work correctly
- Progress updates stream in real-time
- MP3 downloads automatically when ready
- No timeout issues during 20-120s generation
- Auth protects all endpoints
- Works in all modern browsers

## Future Enhancements

(Not in initial implementation)

- Voice preview (play sample before generating)
- Tag history (save/reuse previous tags)
- Batch generation (multiple tags at once)
- Custom voice training
- Export in multiple formats (WAV, OGG, etc.)
