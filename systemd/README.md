# Systemd Unit Files

Automatic break generation scheduling using systemd timers.

## Files

- `generate-break.service` - Oneshot service that runs break generation script
- `generate-break.timer` - Timer that triggers service every 50 minutes

## Installation

```bash
# Copy unit files to systemd directory
sudo cp systemd/generate-break.* /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start timer (will start on boot)
sudo systemctl enable generate-break.timer
sudo systemctl start generate-break.timer
```

## Verification

```bash
# Check timer status
systemctl status generate-break.timer

# List next scheduled runs
systemctl list-timers generate-break.timer

# View service logs
journalctl -u generate-break.service -f

# View recent service runs
journalctl -u generate-break.service --since today
```

## Manual Execution

```bash
# Run break generation immediately
sudo systemctl start generate-break.service

# View output
journalctl -u generate-break.service -n 50
```

## Configuration

Timer schedule: Every 50 minutes (`:00` and `:50` past the hour)
- Matches `break_freshness_minutes` config setting
- Randomized delay: 0-2 minutes
- Persistent: Runs missed scheduled times after boot

Service timeout: 5 minutes
- Break generation should complete in 10-30 seconds typically
- Timeout prevents hung processes

Resource limits:
- Memory: 1GB max
- CPU: 50% quota
- Read-only system except breaks, tmp, and logs directories

## Troubleshooting

### Timer not running
```bash
# Check if timer is enabled
systemctl is-enabled generate-break.timer

# Check timer status
systemctl status generate-break.timer

# Enable if needed
sudo systemctl enable generate-break.timer
sudo systemctl start generate-break.timer
```

### Service failing
```bash
# Check recent logs
journalctl -u generate-break.service -n 100

# Common issues:
# - Missing API keys (check /srv/ai_radio/.env)
# - Network connectivity (check weather/news API access)
# - Permissions (service runs as 'radio' user)
# - Disk space (check /srv/ai_radio/assets/breaks)
```

### Too many/few breaks
Adjust timer schedule in `generate-break.timer`:
```ini
# Run every hour instead of 50 minutes
OnCalendar=hourly

# Run every 30 minutes
OnCalendar=*:00,30:00
```

After editing:
```bash
sudo systemctl daemon-reload
sudo systemctl restart generate-break.timer
```
