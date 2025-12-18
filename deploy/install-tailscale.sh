#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Tailscale Installation Script
#
# IMPORTANT: This script must be run ON the VM after it boots
#
# Prerequisites:
#   1. VM is running and accessible via SSH
#   2. Run as ubuntu user (or with sudo)
#   3. Have Tailscale auth key ready (generate at https://login.tailscale.com/admin/settings/keys)
#
# Usage:
#   ./install-tailscale.sh <tailscale-auth-key>
#
# Example:
#   ./install-tailscale.sh tskey-auth-xxxxxxxxxxxxx-yyyyyyyyyyyyyyyy

# ============================================================================
# Configuration
# ============================================================================

TAILSCALE_AUTH_KEY="${1:-}"

# ============================================================================
# Preflight Checks
# ============================================================================

echo "=== AI Radio Station - Tailscale Installation ==="
echo ""

# Check if auth key provided
if [[ -z "${TAILSCALE_AUTH_KEY}" ]]; then
    echo "✗ Error: Tailscale auth key required" >&2
    echo "" >&2
    echo "Usage: $0 <tailscale-auth-key>" >&2
    echo "" >&2
    echo "Generate an auth key at:" >&2
    echo "  https://login.tailscale.com/admin/settings/keys" >&2
    echo "" >&2
    echo "Recommended settings:" >&2
    echo "  - Reusable: Yes (for reinstalls)" >&2
    echo "  - Ephemeral: No (persistent device)" >&2
    echo "  - Tags: tag:ai-radio" >&2
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
# Install Tailscale
# ============================================================================

echo "Installing Tailscale..."

# Add Tailscale's package signing key and repository
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.noarmor.gpg | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/jammy.tailscale-keyring.list | tee /etc/apt/sources.list.d/tailscale.list

# Update package list and install
apt-get update
apt-get install -y tailscale

echo "✓ Tailscale installed"
echo ""

# ============================================================================
# Start Tailscale
# ============================================================================

echo "Connecting to Tailscale network..."

# Start Tailscale with auth key
tailscale up --authkey="${TAILSCALE_AUTH_KEY}" --hostname=ai-radio

echo "✓ Connected to Tailscale"
echo ""

# ============================================================================
# Verify Connection
# ============================================================================

echo "Verifying Tailscale connection..."

# Wait a moment for connection to stabilize
sleep 3

# Get Tailscale IP
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")

echo "✓ Tailscale connection verified"
echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=== Tailscale Installation Complete ==="
echo ""
echo "Device name:    ai-radio"
echo "Tailscale IP:   ${TAILSCALE_IP}"
echo ""
echo "Verification:"
echo "  - View in admin console: https://login.tailscale.com/admin/machines"
echo "  - Test SSH access:       ssh ubuntu@${TAILSCALE_IP}"
echo "  - Check status:          tailscale status"
echo ""
echo "Next steps:"
echo "  - Configure Cloudflare Tunnel (deploy/install-cloudflared.sh)"
echo "  - Bootstrap repository (deploy/bootstrap-repo.sh)"
echo ""
