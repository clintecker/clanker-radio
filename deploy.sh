#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Deployment Script
# Deploys all fixes to production server

SERVER="ubuntu@10.10.0.86"
REMOTE_BASE="/srv/ai_radio"
LOCAL_BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying AI Radio fixes to ${SERVER}"
echo "========================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Copy updated files to server
echo -e "\n${YELLOW}Step 1: Copying updated files...${NC}"

echo "  → Uploading systemd service files..."
scp "${LOCAL_BASE}/systemd/ai-radio-enqueue.service" "${SERVER}:/tmp/"
scp "${LOCAL_BASE}/systemd/ai-radio-break-scheduler.service" "${SERVER}:/tmp/"
scp "${LOCAL_BASE}/systemd/ai-radio-schedule-station-id.service" "${SERVER}:/tmp/"
scp "${LOCAL_BASE}/systemd/ai-radio-export-nowplaying.service" "${SERVER}:/tmp/"

echo "  → Uploading liquidsoap wrapper..."
scp "${LOCAL_BASE}/systemd/liquidsoap-wrapper.sh" "${SERVER}:/tmp/"

echo "  → Uploading updated scripts..."
scp "${LOCAL_BASE}/scripts/export_now_playing.py" "${SERVER}:/tmp/"
scp "${LOCAL_BASE}/scripts/diagnose_track_selection.py" "${SERVER}:/tmp/"
scp "${LOCAL_BASE}/scripts/enqueue_music.py" "${SERVER}:/tmp/"

echo -e "${GREEN}✓ Files uploaded${NC}"

# Step 2: Deploy systemd changes
echo -e "\n${YELLOW}Step 3: Deploying systemd changes...${NC}"

ssh "${SERVER}" bash <<'ENDSSH'
set -e

echo "  → Moving service files to /etc/systemd/system/..."
sudo mv /tmp/ai-radio-enqueue.service /etc/systemd/system/
sudo mv /tmp/ai-radio-break-scheduler.service /etc/systemd/system/
sudo mv /tmp/ai-radio-schedule-station-id.service /etc/systemd/system/
sudo mv /tmp/ai-radio-export-nowplaying.service /etc/systemd/system/

echo "  → Moving wrapper script to /srv/ai_radio/bin/..."
sudo mv /tmp/liquidsoap-wrapper.sh /srv/ai_radio/bin/
sudo chmod +x /srv/ai_radio/bin/liquidsoap-wrapper.sh
sudo chown ai-radio:ai-radio /srv/ai_radio/bin/liquidsoap-wrapper.sh

echo "  → Moving Python scripts to /srv/ai_radio/scripts/..."
sudo mv /tmp/export_now_playing.py /srv/ai_radio/scripts/
sudo mv /tmp/diagnose_track_selection.py /srv/ai_radio/scripts/
sudo mv /tmp/enqueue_music.py /srv/ai_radio/scripts/
sudo chown ai-radio:ai-radio /srv/ai_radio/scripts/export_now_playing.py
sudo chown ai-radio:ai-radio /srv/ai_radio/scripts/diagnose_track_selection.py
sudo chown ai-radio:ai-radio /srv/ai_radio/scripts/enqueue_music.py
sudo chmod +x /srv/ai_radio/scripts/diagnose_track_selection.py

echo "  → Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "  → Checking service status..."
sudo systemctl status ai-radio-liquidsoap.service --no-pager || true
ENDSSH

echo -e "${GREEN}✓ Systemd changes deployed${NC}"

# Step 3: Run diagnostic script
echo -e "\n${YELLOW}Step 3: Running track selection diagnostic...${NC}"

ssh "${SERVER}" "sudo -u ai-radio ${REMOTE_BASE}/.venv/bin/python ${REMOTE_BASE}/scripts/diagnose_track_selection.py" || true

# Step 4: Clean up abandoned database files
echo -e "\n${YELLOW}Step 4: Cleaning up abandoned database files...${NC}"

ssh "${SERVER}" bash <<'ENDSSH'
set -e

if [ -f /srv/ai_radio/state/radio.db ]; then
    echo "  → Deleting /srv/ai_radio/state/radio.db"
    sudo rm /srv/ai_radio/state/radio.db
else
    echo "  → /srv/ai_radio/state/radio.db already deleted"
fi

if [ -f /srv/ai_radio/db/radio.db ]; then
    echo "  → Deleting /srv/ai_radio/db/radio.db"
    sudo rm /srv/ai_radio/db/radio.db
else
    echo "  → /srv/ai_radio/db/radio.db already deleted"
fi
ENDSSH

echo -e "${GREEN}✓ Database cleanup complete${NC}"

# Step 5: Restart services to apply changes
echo -e "\n${YELLOW}Step 5: Restarting services...${NC}"

read -p "Restart Liquidsoap now? This will cause a brief stream interruption. (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  → Restarting ai-radio-liquidsoap.service..."
    ssh "${SERVER}" "sudo systemctl restart ai-radio-liquidsoap.service"

    echo "  → Waiting 5 seconds for startup..."
    sleep 5

    echo "  → Checking service status..."
    ssh "${SERVER}" "sudo systemctl status ai-radio-liquidsoap.service --no-pager | head -20"

    echo -e "${GREEN}✓ Liquidsoap restarted${NC}"
else
    echo -e "${YELLOW}⚠ Skipping restart - changes will apply on next restart${NC}"
fi

# Step 6: Verify timers are running
echo -e "\n${YELLOW}Step 6: Verifying timers...${NC}"

ssh "${SERVER}" bash <<'ENDSSH'
echo "  → Checking timer status..."
sudo systemctl list-timers ai-radio-* --no-pager

echo ""
echo "  → Checking timer units..."
sudo systemctl status ai-radio-enqueue.timer --no-pager | head -5
sudo systemctl status ai-radio-break-scheduler.timer --no-pager | head -5
sudo systemctl status ai-radio-export-nowplaying.timer --no-pager | head -5
ENDSSH

echo -e "${GREEN}✓ Timer verification complete${NC}"

# Final summary
echo ""
echo "========================================"
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "Changes applied:"
echo "  ✓ Fixed timer death bug (Requires → BindsTo)"
echo "  ✓ Fixed service dependencies"
echo "  ✓ Improved socket readiness check"
echo "  ✓ Fixed metadata lag (Liquidsoap queries)"
echo "  ✓ Fixed track selection (RECENT_HISTORY_SIZE: 50→20, queue: 2-5)"
echo "  ✓ Cleaned up ghost database files"
echo ""
echo "Next steps:"
echo "  1. Monitor stream: https://radio.clintecker.com"
echo "  2. Check logs: ssh ${SERVER} 'sudo journalctl -u ai-radio-liquidsoap -f'"
echo "  3. Verify timers survive restart: sudo systemctl restart ai-radio-liquidsoap"
echo ""
echo "Done! 🚀"
