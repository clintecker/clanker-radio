# Last Byte Radio - SSE Integration Guide

## Overview

Last Byte Radio provides a real-time Server-Sent Events (SSE) endpoint that broadcasts the current playing track, upcoming tracks, recent history, and stream statistics. This guide shows how to integrate the radio's "now playing" data into external websites.

## Quick Start

The SSE endpoint is publicly accessible with CORS enabled, so any website can connect:

```javascript
const eventSource = new EventSource('https://radio.lastbyte.fm/api/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Now playing:', data.current.title, 'by', data.current.artist);
};
```

## Endpoint Details

**URL:** `https://radio.lastbyte.fm/api/stream` (or whatever your radio domain is)

**Method:** GET

**Protocol:** Server-Sent Events (SSE)

**CORS:** Restricted to `*.clintecker.com` domains only

**Response Format:** JSON objects sent as SSE `data:` events

**Access:** The endpoint will return `403 Forbidden` for requests from unauthorized domains. Only pages hosted on `clintecker.com` or any subdomain (e.g., `www.clintecker.com`, `blog.clintecker.com`) can access the stream.

## Data Format

Each SSE message contains a complete state snapshot:

```json
{
  "updated_at": "2025-12-30T01:30:00.000000+00:00",
  "system_status": "online",
  "crossfade": {
    "music_sec": 4.0,
    "breaks_sec": 0.0
  },
  "current": {
    "asset_id": "abc123...",
    "title": "Dial Up Log In and Drop Out",
    "artist": "Clint Ecker",
    "album": "Unknown Album",
    "duration_sec": 187.3,
    "played_at": "2025-12-30T01:18:18.123456+00:00",
    "source": "music",
    "kind": "music"
  },
  "breaks_queue": [],
  "music_queue": [
    {
      "title": "RACK PANAS / 冷風 (Cover)",
      "artist": "Clint Ecker",
      "album": "Unknown Album",
      "duration_sec": 192.5,
      "source": "music"
    }
  ],
  "history": [
    {
      "title": "American Way",
      "artist": "Clint Ecker",
      "played_at": "2025-12-30T01:03:50.000000+00:00",
      "source": "music"
    }
  ],
  "stream": {
    "listeners": 2,
    "bitrate": 128,
    "samplerate": 44100,
    "stream_start_iso8601": "2025-12-30T00:00:00Z"
  }
}
```

### Field Reference

**Top-level fields:**
- `updated_at` - ISO 8601 timestamp of when this state was generated
- `system_status` - `"online"` or `"restarting"`
- `crossfade` - Crossfade durations for music and breaks
- `current` - Currently playing track (see below)
- `breaks_queue` - Upcoming breaks/station IDs (array, max 3)
- `music_queue` - Upcoming music tracks (array, max 5)
- `history` - Recently played tracks (array, max 15)
- `stream` - Stream statistics (see below)

**Current track fields:**
- `asset_id` - Unique identifier for the track
- `title` - Track title
- `artist` - Artist name
- `album` - Album name (may be "Unknown Album")
- `duration_sec` - Track duration in seconds
- `played_at` - ISO 8601 timestamp when track started playing
- `source` - `"music"`, `"break"`, or `"bumper"`
- `kind` - Same as `source` (redundant, kept for compatibility)

**Stream fields:**
- `listeners` - Current listener count
- `bitrate` - Stream bitrate in kbps
- `samplerate` - Audio sample rate in Hz
- `stream_start_iso8601` - When the stream started

## Simple Widget Example

Here's a minimal "now playing" widget for your website:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Last Byte Radio - Now Playing</title>
    <style>
        .radio-widget {
            font-family: 'Courier New', monospace;
            background: #050a05;
            color: #7fff7f;
            padding: 20px;
            border: 1px solid #4a9a4a;
            max-width: 400px;
        }
        .title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .artist {
            font-size: 1em;
            opacity: 0.8;
        }
        .status {
            font-size: 0.8em;
            margin-top: 10px;
            opacity: 0.6;
        }
        .offline {
            color: #ff6b6b;
        }
    </style>
</head>
<body>
    <div class="radio-widget">
        <div class="title" id="track-title">Connecting...</div>
        <div class="artist" id="track-artist"></div>
        <div class="status" id="status">Connecting to stream...</div>
    </div>

    <script>
        const SSE_URL = 'https://radio.lastbyte.fm/api/stream';
        let eventSource = null;

        function connect() {
            eventSource = new EventSource(SSE_URL);

            eventSource.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').classList.remove('offline');
            };

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.current) {
                        document.getElementById('track-title').textContent =
                            data.current.title || 'Unknown Track';
                        document.getElementById('track-artist').textContent =
                            data.current.artist || 'Unknown Artist';
                        document.getElementById('status').textContent =
                            `${data.stream?.listeners || 0} listeners • ${data.stream?.bitrate || 0}kbps`;
                    } else {
                        document.getElementById('track-title').textContent = 'No signal';
                        document.getElementById('track-artist').textContent = '';
                    }
                } catch (error) {
                    console.error('Failed to parse SSE data:', error);
                }
            };

            eventSource.onerror = (error) => {
                console.error('SSE connection error:', error);
                document.getElementById('status').textContent = 'Disconnected - reconnecting...';
                document.getElementById('status').classList.add('offline');
                eventSource.close();

                // Reconnect after 5 seconds
                setTimeout(connect, 5000);
            };
        }

        // Start connection
        connect();
    </script>
</body>
</html>
```

## Advanced: Progress Bar Widget

This example calculates elapsed time and shows a progress bar:

```javascript
class RadioWidget {
    constructor(sseUrl) {
        this.sseUrl = sseUrl;
        this.eventSource = null;
        this.currentTrack = null;
        this.trackStartTime = null;
        this.progressInterval = null;
    }

    connect() {
        this.eventSource = new EventSource(this.sseUrl);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleUpdate(data);
        };

        this.eventSource.onerror = () => {
            this.eventSource.close();
            setTimeout(() => this.connect(), 5000);
        };
    }

    handleUpdate(data) {
        if (!data.current) {
            this.clearProgress();
            return;
        }

        const current = data.current;
        const isNewTrack = !this.currentTrack ||
                          this.currentTrack.asset_id !== current.asset_id;

        if (isNewTrack) {
            this.currentTrack = current;
            this.trackStartTime = new Date(current.played_at);
            this.updateDisplay();
            this.startProgress();
        }
    }

    updateDisplay() {
        // Update your DOM elements here
        document.getElementById('title').textContent = this.currentTrack.title;
        document.getElementById('artist').textContent = this.currentTrack.artist;
        document.getElementById('duration').textContent =
            this.formatTime(this.currentTrack.duration_sec);
    }

    startProgress() {
        this.clearProgress();
        this.progressInterval = setInterval(() => {
            const now = new Date();
            const elapsed = (now - this.trackStartTime) / 1000;
            const duration = this.currentTrack.duration_sec;
            const percent = Math.min((elapsed / duration) * 100, 100);

            document.getElementById('elapsed').textContent = this.formatTime(elapsed);
            document.getElementById('progress-bar').style.width = `${percent}%`;
        }, 500);
    }

    clearProgress() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Usage
const widget = new RadioWidget('https://radio.lastbyte.fm/api/stream');
widget.connect();
```

## Timing Considerations

**Important:** Due to audio crossfading, the `current` track appears in the SSE feed **4-5 seconds before it actually starts playing**. This is by design to allow frontend animations.

If you need precise timing:
- Use `played_at` timestamp to calculate actual elapsed time
- The track becomes audible approximately 4 seconds after `played_at`
- For visual displays, you can start showing the track immediately (matches the radio's own frontend)

## Keepalive Messages

The SSE connection sends keepalive comments every 30 seconds:

```
: keepalive
```

These are comments (start with `:`) and should be ignored by your EventSource handler automatically.

## System Status Events

When the radio is restarting, you'll receive:

```json
{
  "system_status": "restarting",
  "message": "Push service restarting - reconnecting shortly..."
}
```

Your client should handle this gracefully and reconnect automatically (EventSource does this by default).

## Error Handling Best Practices

1. **Always reconnect on error** - Network issues are common, automatic reconnection is essential
2. **Use exponential backoff** - Start with 5s delay, increase on repeated failures
3. **Handle missing data gracefully** - `current` can be `null` during startup/restarts
4. **Validate JSON** - Wrap `JSON.parse()` in try-catch
5. **Show connection status** - Let users know when disconnected

## Security & Rate Limiting

- **Domain Restriction:** Only `*.clintecker.com` domains can access the endpoint
- **Origin Validation:** The server checks the `Origin` header and returns `403 Forbidden` for unauthorized domains
- **No Authentication:** No API keys or tokens required for authorized domains
- **Read-Only:** The endpoint is read-only - clients cannot push data
- **Connection Management:** Keep your connection open - don't repeatedly reconnect unnecessarily
- **Automatic Reconnection:** Use the native EventSource API (handles reconnection automatically)

## Testing Your Integration

Test these scenarios:

1. **Normal operation** - Widget updates when tracks change
2. **Connection loss** - Widget reconnects automatically
3. **No current track** - Handle `current: null` gracefully
4. **Server restart** - Widget shows "reconnecting" and recovers
5. **Long-running** - Connection stays stable for hours

## Support

Questions about integration? Check the codebase:
- SSE server: `scripts/push_daemon.py`
- Frontend example: `nginx/index.html`
- Data export: `scripts/export_now_playing.py`

## Example: clintecker.com Widget

Here's what your clintecker.com widget might look like:

```html
<div id="lastbyte-radio" style="
    font-family: 'Courier New', monospace;
    background: linear-gradient(135deg, #0a1a0a 0%, #050a05 100%);
    color: #7fff7f;
    padding: 15px 20px;
    border: 1px solid #4a9a4a;
    border-radius: 4px;
    box-shadow: 0 0 20px rgba(127, 255, 127, 0.1);
    max-width: 350px;
">
    <div style="font-size: 0.7em; opacity: 0.6; margin-bottom: 8px; letter-spacing: 0.1em;">
        🔊 LAST BYTE RADIO
    </div>
    <div id="lbr-title" style="font-size: 1.1em; font-weight: bold; margin-bottom: 4px;">
        Connecting...
    </div>
    <div id="lbr-artist" style="font-size: 0.9em; opacity: 0.8; margin-bottom: 10px;">
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.75em; opacity: 0.6;">
        <span id="lbr-listeners">— listeners</span>
        <a href="https://radio.lastbyte.fm"
           style="color: #7fff7f; text-decoration: none; border-bottom: 1px dotted;"
           target="_blank">
            Listen Live →
        </a>
    </div>
</div>

<script>
(function() {
    const es = new EventSource('https://radio.lastbyte.fm/api/stream');

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.current) {
            document.getElementById('lbr-title').textContent = data.current.title;
            document.getElementById('lbr-artist').textContent = data.current.artist;
            document.getElementById('lbr-listeners').textContent =
                `${data.stream?.listeners || 0} listeners`;
        }
    };

    es.onerror = () => {
        document.getElementById('lbr-title').textContent = 'Reconnecting...';
        // EventSource reconnects automatically
    };
})();
</script>
```

## License

This integration guide is provided as-is for integrating with Last Byte Radio. The SSE endpoint is publicly accessible for display purposes.
