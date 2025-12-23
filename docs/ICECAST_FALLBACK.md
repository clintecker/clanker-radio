# Icecast Fallback Mount Configuration

## Overview

Configure Icecast to automatically redirect listeners to a fallback mount (`/radio-fallback`) when the main mount (`/radio`) disconnects, then redirect them back when it reconnects.

This ensures zero dead air during:
- Liquidsoap restarts
- Config deployments
- System maintenance
- Unexpected disconnections

## Prerequisites

1. ✅ Technical difficulties audio track at `/srv/ai_radio/assets/technical_difficulties.mp3`
2. ✅ Fallback Liquidsoap config at `/srv/ai_radio/config/fallback.liq`
3. ✅ Fallback systemd service installed

## Icecast Configuration

Edit `/etc/icecast2/icecast.xml` and add this mount configuration inside the `<icecast>` section:

```xml
<!-- Main mount with fallback configuration -->
<mount>
    <mount-name>/radio</mount-name>

    <!-- Fallback mount to use when this mount disconnects -->
    <fallback-mount>/radio-fallback</fallback-mount>

    <!-- Override: when main reconnects, redirect listeners back from fallback -->
    <fallback-override>1</fallback-override>

    <!-- How long to wait before triggering fallback (seconds) -->
    <fallback-when-full>0</fallback-when-full>

    <!-- Keep listeners connected during source reconnect -->
    <burst-on-connect>1</burst-on-connect>

    <!-- Public mount -->
    <public>1</public>
</mount>

<!-- Fallback mount (fed by fallback Liquidsoap instance) -->
<mount>
    <mount-name>/radio-fallback</mount-name>

    <!-- Hidden from directory listings -->
    <public>0</public>
    <hidden>1</hidden>

    <!-- Stream info -->
    <stream-name>LAST BYTE RADIO - Technical Difficulties</stream-name>
    <stream-description>Back shortly</stream-description>
    <stream-url>https://radio.clintecker.com</stream-url>
    <genre>Broadcast Interruption</genre>
</mount>
```

## Installation Steps

### 1. Deploy Fallback Config and Service

```bash
# From local machine
./scripts/deploy.sh

# Or manually:
scp config/fallback.liq clint@10.10.0.86:/tmp/
scp systemd/ai-radio-liquidsoap-fallback.service clint@10.10.0.86:/tmp/

ssh clint@10.10.0.86 << 'EOF'
sudo mv /tmp/fallback.liq /srv/ai_radio/config/
sudo chown ai-radio:ai-radio /srv/ai_radio/config/fallback.liq

sudo mv /tmp/ai-radio-liquidsoap-fallback.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-radio-liquidsoap-fallback
EOF
```

### 2. Update Icecast Configuration

```bash
ssh clint@10.10.0.86

# Backup current config
sudo cp /etc/icecast2/icecast.xml /etc/icecast2/icecast.xml.backup

# Edit config (add mount configurations above)
sudo nano /etc/icecast2/icecast.xml

# Restart Icecast to apply changes
sudo systemctl restart icecast2
```

### 3. Start Fallback Liquidsoap

```bash
# Start fallback instance
sudo systemctl start ai-radio-liquidsoap-fallback

# Check status
sudo systemctl status ai-radio-liquidsoap-fallback

# Verify it's streaming to /radio-fallback
curl -I http://localhost:8000/radio-fallback
```

## Testing

### Test Fallback Behavior

```bash
# 1. Start listening to main mount
curl http://localhost:8000/radio > /dev/null &
MAIN_PID=$!

# 2. Restart main Liquidsoap
sudo systemctl restart ai-radio-liquidsoap

# 3. Observer: listener should seamlessly switch to fallback, then back
# Check Icecast logs:
sudo journalctl -u icecast2 -f
```

Expected log sequence:
1. `/radio` disconnects (main Liquidsoap restarting)
2. Client redirected to `/radio-fallback` (fallback kicks in)
3. `/radio` reconnects (main Liquidsoap back online)
4. Client redirected back to `/radio` (fallback-override)

### Manual Testing

1. **Play main stream:** http://localhost:8000/radio
2. **Restart main:** `sudo systemctl restart ai-radio-liquidsoap`
3. **Observe:** Should hear technical difficulties loop briefly, then resume normal programming
4. **No dead air!**

## Monitoring

```bash
# Check both Liquidsoap instances
sudo systemctl status ai-radio-liquidsoap          # Main
sudo systemctl status ai-radio-liquidsoap-fallback  # Fallback

# Check Icecast mounts
curl -s http://localhost:8000/admin/stats | grep -A5 "mount-name"

# Check logs
sudo journalctl -u ai-radio-liquidsoap -f          # Main logs
sudo journalctl -u ai-radio-liquidsoap-fallback -f  # Fallback logs
```

## Troubleshooting

**Fallback not triggering:**
- Check `fallback-override` is set to `1` in Icecast config
- Verify fallback Liquidsoap is running and connected to `/radio-fallback`
- Check Icecast logs: `sudo journalctl -u icecast2 -f`

**Listeners not redirecting back:**
- Ensure `fallback-override` is enabled (redirects back when main reconnects)
- Check main Liquidsoap successfully reconnected: `systemctl status ai-radio-liquidsoap`

**Technical difficulties track not looping:**
- Verify file exists: `ls -lh /srv/ai_radio/assets/technical_difficulties.mp3`
- Check fallback logs: `journalctl -u ai-radio-liquidsoap-fallback -f`
- Test file manually: `ffplay /srv/ai_radio/assets/technical_difficulties.mp3`

## References

- [Icecast Mount Configuration](https://icecast.org/docs/icecast-trunk/config-file.html#mount)
- [Liquidsoap Single Operator](https://www.liquidsoap.info/doc-2.4.0/reference.html#single)
