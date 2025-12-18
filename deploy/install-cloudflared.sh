#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Cloudflared Tunnel Installation Script
#
# IMPORTANT: This script must be run ON the VM after Tailscale is configured
#
# Prerequisites:
#   1. VM is running and accessible
#   2. Run as ubuntu user (or with sudo)
#   3. Have Cloudflare tunnel token ready
#      (Create tunnel at: https://one.dash.cloudflare.com/ → Zero Trust → Networks → Tunnels)
#
# Usage:
#   ./install-cloudflared.sh <tunnel-token>
#
# Example:
#   ./install-cloudflared.sh eyJhIjoixxxxxxxxx...

# ============================================================================
# Configuration
# ============================================================================

TUNNEL_TOKEN="${1:-}"

# ============================================================================
# Preflight Checks
# ============================================================================

echo "=== AI Radio Station - Cloudflared Tunnel Installation ==="
echo ""

# Check if tunnel token provided
if [[ -z "${TUNNEL_TOKEN}" ]]; then
    echo "✗ Error: Cloudflare tunnel token required" >&2
    echo "" >&2
    echo "Usage: $0 <tunnel-token>" >&2
    echo "" >&2
    echo "Create a tunnel at:" >&2
    echo "  https://one.dash.cloudflare.com/" >&2
    echo "  → Zero Trust → Networks → Tunnels → Create a tunnel" >&2
    echo "" >&2
    echo "Configuration:" >&2
    echo "  1. Create tunnel with name: ai-radio" >&2
    echo "  2. Add public hostname:" >&2
    echo "     - Domain: your.domain.com" >&2
    echo "     - Service: http://localhost:8000" >&2
    echo "  3. Copy the tunnel token (starts with 'eyJ...')" >&2
    exit 1
fi

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
    echo "This script requires root privileges. Re-running with sudo..." >&2
    exec sudo "$0" "$@"
fi

echo "✓ Preflight checks passed"
echo ""

# ============================================================================
# Install Cloudflared
# ============================================================================

echo "Installing cloudflared..."

# Add cloudflare gpg key
mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Add cloudflare repo
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | tee /etc/apt/sources.list.d/cloudflared.list

# Update and install
apt-get update
apt-get install -y cloudflared

echo "✓ Cloudflared installed"
echo ""

# ============================================================================
# Configure Tunnel
# ============================================================================

echo "Configuring tunnel..."

# Install tunnel service with token
cloudflared service install "${TUNNEL_TOKEN}"

echo "✓ Tunnel configured"
echo ""

# ============================================================================
# Start Service
# ============================================================================

echo "Starting cloudflared service..."

# Enable and start service
systemctl enable cloudflared
systemctl start cloudflared

# Wait for service to initialize
sleep 3

echo "✓ Service started"
echo ""

# ============================================================================
# Verify Service
# ============================================================================

echo "Verifying tunnel connection..."

# Check service status
if systemctl is-active --quiet cloudflared; then
    echo "✓ Cloudflared service is running"
else
    echo "✗ Warning: Service may not be running properly" >&2
    echo "  Check logs: journalctl -u cloudflared -n 50" >&2
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=== Cloudflared Installation Complete ==="
echo ""
echo "Service status: $(systemctl is-active cloudflared)"
echo ""
echo "Verification:"
echo "  - Check tunnel status: cloudflared tunnel info"
echo "  - View logs:           journalctl -u cloudflared -f"
echo "  - Service status:      systemctl status cloudflared"
echo "  - Test your domain:    curl -I https://your.domain.com"
echo ""
echo "Tunnel should now route traffic from your domain to http://localhost:8000"
echo ""
echo "Next steps:"
echo "  - Bootstrap repository (deploy/bootstrap-repo.sh)"
echo "  - Verify Icecast is accessible at your domain once installed"
echo ""
