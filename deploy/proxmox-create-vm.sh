#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Proxmox VM Creation Script
#
# IMPORTANT: This script must be run ON the Proxmox host (proxmox-chi)
#
# Prerequisites:
#   1. Ubuntu 22.04 cloud image downloaded
#   2. cloud-init-user-data.yaml prepared (run prepare-cloud-init.sh first)
#   3. Run with sudo/root privileges
#
# Usage:
#   sudo ./proxmox-create-vm.sh

# ============================================================================
# Configuration
# ============================================================================

VM_ID=150
VM_NAME="ai-radio"
VM_MEMORY=4096          # 4GB RAM
VM_CORES=2              # 2 CPU cores
VM_DISK_SIZE=100G       # 100GB disk
VM_STORAGE="local-lvm"  # Proxmox storage pool

# Ubuntu cloud image
UBUNTU_IMAGE_URL="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
UBUNTU_IMAGE_FILE="/var/lib/vz/template/iso/ubuntu-22.04-cloudimg-amd64.img"

# Cloud-init files (must be in same directory as this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD_INIT_USER_DATA="${SCRIPT_DIR}/cloud-init-user-data.yaml"
CLOUD_INIT_NETWORK_CONFIG="${SCRIPT_DIR}/cloud-init-network-config.yaml"

# ============================================================================
# Preflight Checks
# ============================================================================

echo "=== AI Radio Station - Proxmox VM Creation ==="
echo ""

# Check if running on Proxmox
if ! command -v qm &> /dev/null; then
    echo "✗ Error: 'qm' command not found. This script must run on a Proxmox host." >&2
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "✗ Error: This script must be run as root (use sudo)" >&2
   exit 1
fi

# Check if cloud-init user-data exists
if [[ ! -f "${CLOUD_INIT_USER_DATA}" ]]; then
    echo "✗ Error: Cloud-init user-data not found: ${CLOUD_INIT_USER_DATA}" >&2
    echo "  Run prepare-cloud-init.sh first to generate this file" >&2
    exit 1
fi

# Check if VM ID already exists
if qm status "${VM_ID}" &> /dev/null; then
    echo "✗ Error: VM ${VM_ID} already exists" >&2
    echo "  To recreate, first destroy with: qm destroy ${VM_ID}" >&2
    exit 1
fi

echo "✓ Preflight checks passed"
echo ""

# ============================================================================
# Download Ubuntu Cloud Image (if needed)
# ============================================================================

if [[ ! -f "${UBUNTU_IMAGE_FILE}" ]]; then
    echo "Downloading Ubuntu 22.04 cloud image..."
    mkdir -p "$(dirname "${UBUNTU_IMAGE_FILE}")"
    wget -O "${UBUNTU_IMAGE_FILE}" "${UBUNTU_IMAGE_URL}"
    echo "✓ Image downloaded"
else
    echo "✓ Ubuntu cloud image already present"
fi

echo ""

# ============================================================================
# Create VM
# ============================================================================

echo "Creating VM ${VM_ID} (${VM_NAME})..."

# Create the VM
qm create "${VM_ID}" \
    --name "${VM_NAME}" \
    --memory "${VM_MEMORY}" \
    --cores "${VM_CORES}" \
    --net0 virtio,bridge=vmbr0

echo "✓ VM created"

# Import the Ubuntu cloud image as a disk
echo "Importing Ubuntu cloud image as VM disk..."
qm importdisk "${VM_ID}" "${UBUNTU_IMAGE_FILE}" "${VM_STORAGE}"

echo "✓ Disk imported"

# Attach the disk to the VM
echo "Configuring VM storage..."
qm set "${VM_ID}" --scsihw virtio-scsi-pci --scsi0 "${VM_STORAGE}:vm-${VM_ID}-disk-0"

# Resize the disk
qm resize "${VM_ID}" scsi0 "${VM_DISK_SIZE}"

echo "✓ Storage configured (${VM_DISK_SIZE})"

# Add cloud-init drive
echo "Adding cloud-init drive..."
qm set "${VM_ID}" --ide2 "${VM_STORAGE}:cloudinit"

echo "✓ Cloud-init drive added"

# Set boot order (boot from scsi0)
qm set "${VM_ID}" --boot c --bootdisk scsi0

# Enable QEMU guest agent
qm set "${VM_ID}" --agent enabled=1

# Set VGA display
qm set "${VM_ID}" --vga std

echo "✓ VM hardware configured"

# ============================================================================
# Configure Cloud-Init
# ============================================================================

echo "Configuring cloud-init..."

# Set cloud-init user data
qm set "${VM_ID}" --cicustom "user=local:snippets/ai-radio-user-data.yaml"

# Copy cloud-init files to Proxmox snippets directory
SNIPPETS_DIR="/var/lib/vz/snippets"
mkdir -p "${SNIPPETS_DIR}"

cp "${CLOUD_INIT_USER_DATA}" "${SNIPPETS_DIR}/ai-radio-user-data.yaml"
cp "${CLOUD_INIT_NETWORK_CONFIG}" "${SNIPPETS_DIR}/ai-radio-network-config.yaml"

# Set network config
qm set "${VM_ID}" --cicustom "user=local:snippets/ai-radio-user-data.yaml,network=local:snippets/ai-radio-network-config.yaml"

# Set cloud-init IP config to DHCP
qm set "${VM_ID}" --ipconfig0 ip=dhcp

echo "✓ Cloud-init configured"

# ============================================================================
# Final Configuration
# ============================================================================

echo "Applying final configuration..."

# Set description
qm set "${VM_ID}" --description "AI Radio Station - 24/7 Icecast Streaming Server"

# Enable start at boot
qm set "${VM_ID}" --onboot 1

echo "✓ Final configuration applied"
echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=== VM Creation Complete ==="
echo ""
echo "VM ID:     ${VM_ID}"
echo "VM Name:   ${VM_NAME}"
echo "Memory:    ${VM_MEMORY}MB"
echo "CPU Cores: ${VM_CORES}"
echo "Disk Size: ${VM_DISK_SIZE}"
echo ""
echo "Next steps:"
echo "  1. Start the VM:     qm start ${VM_ID}"
echo "  2. Monitor startup:  qm status ${VM_ID}"
echo "  3. Get IP address:   qm guest cmd ${VM_ID} network-get-interfaces"
echo "  4. Connect via SSH:  ssh ubuntu@<ip-address>"
echo ""
echo "After VM boots (~60 seconds):"
echo "  - SSH access will be available using your configured SSH key"
echo "  - Continue with Tailscale installation (deploy/install-tailscale.sh)"
echo ""
