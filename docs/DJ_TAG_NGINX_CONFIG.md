# DJ Tag Generator Nginx Configuration

## Overview

Add these sections to `/etc/nginx/sites-enabled/radio` on the server to enable DJ tag generator with HTTP Basic Auth and SSE support.

## Configuration Changes

### 1. Add upstream definition (after existing upstreams)

```nginx
upstream dj_tag_api {
    server 127.0.0.1:5001;
}
```

### 2. Add location for HTML page (in server block)

```nginx
location /admin/dj-tag.html {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
    alias /srv/ai_radio/public/admin/dj_tag.html;
}
```

### 3. Add location for API endpoints (in server block)

```nginx
location /api/dj-tag/ {
    auth_basic "Radio Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # SSE-specific headers
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 180s;
    proxy_connect_timeout 10s;
    proxy_send_timeout 180s;

    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Proxy to Flask API
    proxy_pass http://dj_tag_api/;
}
```

## Deployment Steps

1. SSH to server: `ssh clint@10.10.0.86`
2. Edit nginx config: `sudo nano /etc/nginx/sites-enabled/radio`
3. Add the three sections above
4. Test configuration: `sudo nginx -t`
5. Reload nginx: `sudo systemctl reload nginx`

## Verification

Test that auth is required:
```bash
curl -I https://radio.clintecker.com/admin/dj-tag.html
# Should return 401 Unauthorized
```

Test with auth (replace with actual credentials):
```bash
curl -u admin:password https://radio.clintecker.com/admin/dj-tag.html
# Should return 200 OK with HTML
```

## SSE Timeout Configuration

The configuration includes:
- `proxy_buffering off` - Disable buffering for real-time SSE
- `proxy_cache off` - Disable caching for SSE streams
- `proxy_read_timeout 180s` - Allow up to 3 minutes for generation
- `proxy_send_timeout 180s` - Allow up to 3 minutes for sending response

These timeouts match the backend's maximum generation time of 120 seconds plus buffer.
