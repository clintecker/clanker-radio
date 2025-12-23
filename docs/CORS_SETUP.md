# CORS Setup for Now Playing API

## Overview

Enable Cross-Origin Resource Sharing (CORS) for `now_playing.json` so it can be fetched from clintecker.com/www.clintecker.com via JavaScript.

## Nginx Configuration

Edit the nginx site config for radio.clintecker.com (typically at `/etc/nginx/sites-available/radio.clintecker.com`):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name radio.clintecker.com;

    root /srv/ai_radio/public;
    index index.html;

    # Enable CORS for now_playing.json
    location = /now_playing.json {
        # Allow requests from clintecker.com domains
        add_header 'Access-Control-Allow-Origin' 'https://clintecker.com' always;
        add_header 'Access-Control-Allow-Origin' 'https://www.clintecker.com' always;

        # Allow credentials (cookies, authorization headers)
        add_header 'Access-Control-Allow-Credentials' 'true' always;

        # Cache for 5 seconds (matches export interval)
        add_header 'Cache-Control' 'public, max-age=5';

        # Return JSON content type
        default_type application/json;

        try_files $uri =404;
    }

    # Regular static files (no CORS)
    location / {
        try_files $uri $uri/ =404;
    }

    # Icecast proxy
    location /radio {
        proxy_pass http://127.0.0.1:8000/radio;
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
```

## Alternative: Allow All Origins (Less Secure)

If you want to allow any website to fetch the data:

```nginx
location = /now_playing.json {
    # Allow all origins
    add_header 'Access-Control-Allow-Origin' '*' always;

    # Cache for 5 seconds
    add_header 'Cache-Control' 'public, max-age=5';

    default_type application/json;
    try_files $uri =404;
}
```

## Implementation Steps

### 1. Edit Nginx Config

```bash
ssh clint@10.10.0.86

# Backup current config
sudo cp /etc/nginx/sites-available/radio.clintecker.com /etc/nginx/sites-available/radio.clintecker.com.backup

# Edit config (add location block above)
sudo nano /etc/nginx/sites-available/radio.clintecker.com

# Test config syntax
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 2. Test CORS Headers

```bash
# From local machine, test CORS headers
curl -H "Origin: https://clintecker.com" \
     -H "Access-Control-Request-Method: GET" \
     -I https://radio.clintecker.com/now_playing.json

# Should see:
# Access-Control-Allow-Origin: https://clintecker.com
```

### 3. Test JavaScript Fetch

Add this to clintecker.com page:

```javascript
fetch('https://radio.clintecker.com/now_playing.json')
  .then(response => response.json())
  .then(data => {
    console.log('Now playing:', data);
    // Display track info on your website
  })
  .catch(error => console.error('CORS error:', error));
```

## Now Playing JSON Format

The endpoint returns:

```json
{
  "title": "MALWARE GROOVE",
  "artist": "Clint Ecker",
  "album": null,
  "filename": "/srv/ai_radio/assets/music/907ebdfa6519ebef021ae4b6e7f3179900022d766c61dc3aafc69a43fc6f5702.mp3",
  "source_type": "music",
  "timestamp": "2025-12-23T02:51:42Z"
}
```

## Troubleshooting

**CORS error in browser console:**
- Check nginx config applied: `sudo nginx -t && sudo systemctl reload nginx`
- Verify headers: `curl -I https://radio.clintecker.com/now_playing.json`
- Check browser developer tools Network tab for response headers

**File not found (404):**
- Verify export service running: `systemctl status ai-radio-export-nowplaying.timer`
- Check file exists: `ls -lh /srv/ai_radio/public/now_playing.json`
- Check permissions: `sudo chmod 644 /srv/ai_radio/public/now_playing.json`

**Stale data:**
- Verify export timer running: `systemctl list-timers ai-radio-export-nowplaying.timer`
- Check logs: `journalctl -u ai-radio-export-nowplaying.service -f`
- Manual trigger: `sudo systemctl start ai-radio-export-nowplaying.service`
