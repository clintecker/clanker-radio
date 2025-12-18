#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Cloud-Init Preparation Script
# Substitutes SSH public key into cloud-init user-data template

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="${SCRIPT_DIR}/cloud-init-user-data.yaml.template"
OUTPUT_FILE="${SCRIPT_DIR}/cloud-init-user-data.yaml"

# Default SSH public key location
SSH_KEY_PATH="${HOME}/.ssh/id_ed25519.pub"

# Allow override via environment variable
if [[ -n "${AI_RADIO_SSH_KEY:-}" ]]; then
    SSH_KEY_PATH="${AI_RADIO_SSH_KEY}"
fi

# Validate inputs
if [[ ! -f "${TEMPLATE_FILE}" ]]; then
    echo "✗ Error: Template file not found: ${TEMPLATE_FILE}" >&2
    exit 1
fi

if [[ ! -f "${SSH_KEY_PATH}" ]]; then
    echo "✗ Error: SSH public key not found: ${SSH_KEY_PATH}" >&2
    echo "  Tip: Set AI_RADIO_SSH_KEY environment variable to use a different key" >&2
    exit 1
fi

# Read SSH public key
SSH_PUBLIC_KEY=$(cat "${SSH_KEY_PATH}")

# Substitute into template using envsubst
export SSH_PUBLIC_KEY
envsubst < "${TEMPLATE_FILE}" > "${OUTPUT_FILE}"

echo "✓ Generated cloud-init user-data: ${OUTPUT_FILE}"
echo "  Using SSH key: ${SSH_KEY_PATH}"
echo ""
echo "Next steps:"
echo "  1. Review ${OUTPUT_FILE}"
echo "  2. Run proxmox-create-vm.sh to create the VM"
