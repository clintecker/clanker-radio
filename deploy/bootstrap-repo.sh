#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Repository Bootstrap Script
#
# IMPORTANT: This script must be run ON the VM after infrastructure is ready
#
# Prerequisites:
#   1. VM is running
#   2. Tailscale is configured
#   3. Run as ubuntu user (will use sudo as needed)
#   4. SSH key is configured for GitHub access
#
# Usage:
#   ./bootstrap-repo.sh [branch]
#
# Example:
#   ./bootstrap-repo.sh main

# ============================================================================
# Configuration
# ============================================================================

REPO_URL="git@github.com:your-username/ai-radio-station.git"
REPO_DIR="/srv/ai_radio"
BRANCH="${1:-main}"

# ============================================================================
# Preflight Checks
# ============================================================================

echo "=== AI Radio Station - Repository Bootstrap ==="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "✗ Error: git is not installed" >&2
    exit 1
fi

# Check if repository directory already exists
if [[ -d "${REPO_DIR}" ]]; then
    echo "✗ Error: Repository directory already exists: ${REPO_DIR}" >&2
    echo "  This script should only be run once during initial setup" >&2
    exit 1
fi

echo "✓ Preflight checks passed"
echo ""

# ============================================================================
# Clone Repository
# ============================================================================

echo "Cloning repository..."
echo "  URL: ${REPO_URL}"
echo "  Branch: ${BRANCH}"
echo "  Destination: ${REPO_DIR}"
echo ""

# Create parent directory with sudo
sudo mkdir -p /srv
sudo chown ubuntu:ubuntu /srv

# Clone repository
git clone --branch "${BRANCH}" "${REPO_URL}" "${REPO_DIR}"

echo "✓ Repository cloned"
echo ""

# ============================================================================
# Verify Clone
# ============================================================================

echo "Verifying repository..."

cd "${REPO_DIR}"

# Check git status
CURRENT_BRANCH=$(git branch --show-current)
COMMIT_HASH=$(git rev-parse --short HEAD)

if [[ "${CURRENT_BRANCH}" != "${BRANCH}" ]]; then
    echo "✗ Warning: On branch '${CURRENT_BRANCH}', expected '${BRANCH}'" >&2
fi

echo "✓ Repository verified"
echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=== Repository Bootstrap Complete ==="
echo ""
echo "Repository:     ${REPO_DIR}"
echo "Branch:         ${CURRENT_BRANCH}"
echo "Commit:         ${COMMIT_HASH}"
echo ""
echo "Next steps:"
echo "  1. cd ${REPO_DIR}"
echo "  2. Follow implementation plans starting with Phase 0 (Foundation)"
echo "  3. See docs/plans/ for detailed implementation steps"
echo ""
echo "Phase execution order:"
echo "  - Phase 0:  Foundation (user, directories, database)"
echo "  - Phase 1:  Core Infrastructure (Icecast, Liquidsoap)"
echo "  - Phase 2:  Asset Management (track ingestion, metadata)"
echo "  - Phase 3:  Liquidsoap Advanced (multi-queue, fallback)"
echo "  - Phase 4:  Content Generation (AI breaks, TTS)"
echo "  - Phase 5:  Scheduling & Orchestration (queue management)"
echo "  - Phase 6:  Observability & Monitoring (health checks, logging)"
echo "  - Phase 7:  Operator Tools (manual controls)"
echo "  - Phase 8:  Testing & Documentation (integration tests)"
echo ""
