# Now Playing API

Simple cached JSON endpoint for external clients to fetch stream status.

**Public URL:** https://radio.clintecker.com/api/now_playing.json

## Endpoints

### GET /api/now_playing.json

**Public:** https://radio.clintecker.com/api/now_playing.json
**Local:** http://localhost/api/now_playing.json

Returns current, next, and recent tracks.

**Example Response:**
```json
{
  "updated_at": "2025-12-21T04:35:41+00:00",
  "current": {
    "asset_id": "d5f42c4082f8e23c...",
    "title": "Neon Dreams",
    "artist": "Synthwave Collective",
    "album": "Cyber Nights",
    "played_at": "2025-12-21T04:35:41+00:00",
    "source": "music"
  },
  "next": {
    "rid": "10",
    "filename": "/srv/ai_radio/assets/music/17a26d05...",
    "title": "Digital Horizon",
    "artist": "RetroWave"
  },
  "history": [
    {
      "asset_id": "b309aaacb2940e15...",
      "title": "Tokyo Lights",
      "artist": "City Pop Revival",
      "played_at": "2025-12-21T04:32:15+00:00",
      "source": "music"
    }
  ]
}
```

**Cache Behavior:**
- JSON file updates every 30 seconds (via systemd timer)
- Nginx caches for 30 seconds (`Cache-Control: public, max-age=30`)
- Cloudflare may add additional edge caching
- Max staleness: ~60 seconds (plus Cloudflare edge cache)

**Note:** Cloudflare is configured to allow nginx's cache headers to control caching behavior.

## Deployment

1. **Deploy script and systemd units:**
```bash
# Copy files
scp scripts/export_now_playing.py ubuntu@radio:/tmp/
scp systemd/ai-radio-export-nowplaying.{service,timer} ubuntu@radio:/tmp/

# Install
ssh ubuntu@radio
sudo cp /tmp/export_now_playing.py /srv/ai_radio/scripts/
sudo chmod +x /srv/ai_radio/scripts/export_now_playing.py
sudo cp /tmp/ai-radio-export-nowplaying.service /etc/systemd/system/
sudo cp /tmp/ai-radio-export-nowplaying.timer /etc/systemd/system/
```

2. **Create public directory:**
```bash
sudo mkdir -p /srv/ai_radio/public
sudo chown ai-radio:ai-radio /srv/ai_radio/public
```

3. **Enable and start timer:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-radio-export-nowplaying.timer
sudo systemctl start ai-radio-export-nowplaying.timer
```

4. **Verify it's running:**
```bash
# Check timer status
sudo systemctl list-timers ai-radio-export-nowplaying.timer

# Check JSON file
cat /srv/ai_radio/public/now_playing.json

# Check logs
sudo journalctl -u ai-radio-export-nowplaying.service -f
```

5. **Configure Nginx:**
```bash
# Add to your radio.clintecker.com server block
sudo nano /etc/nginx/sites-available/radio.clintecker.com

# Include the location block from nginx/now_playing.conf
# Then reload:
sudo nginx -t && sudo systemctl reload nginx
```

## Usage from Website

**JavaScript:**
```javascript
fetch('https://radio.clintecker.com/api/now_playing.json')
  .then(r => r.json())
  .then(data => {
    console.log('Current:', data.current.title);
    console.log('Next:', data.next.title);
    console.log('History:', data.history);
  });
```

**React Hook:**
```javascript
function useNowPlaying() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      const res = await fetch('/api/now_playing.json');
      setData(await res.json());
    };

    fetch();
    const interval = setInterval(fetch, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  return data;
}
```

## Notes

- Updates every 30 seconds (low overhead)
- Cached static file (no database load per request)
- CORS enabled for external sites
- Falls back gracefully if data unavailable
- Next track requires music in queue (shows null if queue empty)
