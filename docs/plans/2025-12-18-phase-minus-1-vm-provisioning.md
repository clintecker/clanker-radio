# Phase -1: VM Provisioning & Deployment - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provision Ubuntu VM on proxmox-chi, configure networking with Tailscale and Cloudflared tunnel to radio.clintecker.com, and bootstrap repository deployment

**Architecture:** Create VM from Proxmox template using cloud-init for initial configuration. Install Tailscale for secure administrative access. Set up Cloudflared tunnel to expose Icecast stream publicly at radio.clintecker.com. Create professional bootstrap script to clone repository and begin Phase 0.

**Tech Stack:** Proxmox VE, Ubuntu 22.04 cloud image, cloud-init, Tailscale, Cloudflare Tunnels, Git

---

## Prerequisites

**Required Information:**
- Proxmox host: `proxmox-chi`
- VM template name (e.g., `ubuntu-22.04-cloud`)
- CLiNT's SSH public key
- Tailscale auth key (ephemeral or reusable)
- Cloudflare account with tunnel capability
- GitHub repository URL: `https://github.com/clintecker/clanker-radio.git`

**Network Requirements:**
- VM needs internet access for package installation
- Tailscale for secure administrative access
- Cloudflared tunnel for public HTTP access to Icecast (port 8000)

---

## Task 1: Proxmox VM Creation

**Files:**
- Create: `./deploy/proxmox-create-vm.sh`
- Create: `./deploy/cloud-init-user-data.yaml.template`
- Create: `./deploy/cloud-init-network-config.yaml`
- Create: `./deploy/prepare-cloud-init.sh`

**Step 1: Create cloud-init user-data template**

Create file `./deploy/cloud-init-user-data.yaml.template`:
```yaml
#cloud-config
# AI Radio Station - Cloud-Init User Data
# Proxmox VM initial configuration

hostname: ai-radio-1
fqdn: ai-radio-1.clintecker.com

# Timezone configuration
timezone: America/Chicago

# User configuration
users:
  - name: clint
    groups: [sudo, adm]
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    lock_passwd: false
    ssh_authorized_keys:
      - ${SSH_PUBLIC_KEY}

# Package management
package_update: true
package_upgrade: true

# Essential packages
packages:
  - curl
  - wget
  - git
  - vim
  - htop
  - tree
  - jq
  - sqlite3
  - net-tools
  - dnsutils
  - ca-certificates
  - apt-transport-https
  - software-properties-common

# Write pre-deployment scripts
write_files:
  - path: /etc/ai-radio-version
    content: |
      AI Radio Station
      Provisioned: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
      Phase: -1 (VM Provisioning)
    permissions: '0644'

  - path: /usr/local/bin/ai-radio-info
    content: |
      #!/bin/bash
      # AI Radio Station - System Information
      echo "=== AI Radio Station VM ==="
      echo "Hostname: $(hostname)"
      echo "OS: $(lsb_release -d | cut -f2)"
      echo "Kernel: $(uname -r)"
      echo "Uptime: $(uptime -p)"
      echo ""
      echo "Tailscale Status:"
      tailscale status 2>/dev/null || echo "  Not configured"
      echo ""
      echo "Cloudflared Status:"
      systemctl is-active cloudflared 2>/dev/null || echo "  Not configured"
      echo ""
      [ -f /etc/ai-radio-version ] && cat /etc/ai-radio-version
    permissions: '0755'

# System configuration
runcmd:
  # Set timezone
  - timedatectl set-timezone America/Chicago
  - systemctl enable systemd-timesyncd
  - systemctl start systemd-timesyncd

  # Ensure SSH is enabled and running
  - systemctl enable ssh
  - systemctl start ssh

  # Create deployment marker
  - touch /var/lib/cloud/instance/ai-radio-provisioned
  - date -u > /var/lib/cloud/instance/provisioned-timestamp

# Final message
final_message: |
  AI Radio Station VM provisioning complete!
  Uptime: $UPTIME

  Next steps:
  1. Connect via Tailscale: ssh clint@ai-radio-1
  2. Run: /srv/ai_radio/deploy/bootstrap.sh

  The system is ready for Phase 0 (Foundation).
```

Run:
```bash
mkdir -p /Users/clint/code/clintecker/clanker-radio/deploy
cat > /Users/clint/code/clintecker/clanker-radio/deploy/cloud-init-user-data.yaml.template << 'EOF'
[content above]
EOF
```

Expected: Cloud-init user-data template created

**Step 2: Create cloud-init preparation script**

Create file `./deploy/prepare-cloud-init.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Cloud-Init Preparation
# Uses envsubst to inject SSH key into cloud-init template

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/cloud-init-user-data.yaml.template"
OUTPUT="$SCRIPT_DIR/cloud-init-user-data.yaml"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

# Check if template exists
if [ ! -f "$TEMPLATE" ]; then
    error "Template not found: $TEMPLATE"
fi

# Get SSH public key
SSH_KEY_FILE="${SSH_KEY_FILE:-$HOME/.ssh/id_ed25519.pub}"
if [ ! -f "$SSH_KEY_FILE" ]; then
    SSH_KEY_FILE="$HOME/.ssh/id_rsa.pub"
fi

if [ ! -f "$SSH_KEY_FILE" ]; then
    error "No SSH public key found. Checked: ~/.ssh/id_ed25519.pub and ~/.ssh/id_rsa.pub"
fi

export SSH_PUBLIC_KEY=$(cat "$SSH_KEY_FILE")

log "Using SSH key from: $SSH_KEY_FILE"
log "Generating cloud-init configuration..."

# Use envsubst to replace variables
envsubst < "$TEMPLATE" > "$OUTPUT"

if [ $? -ne 0 ]; then
    error "Failed to generate cloud-init configuration"
fi

log "Cloud-init configuration ready: $OUTPUT"
log ""
log "Next step: Copy to Proxmox and create VM"
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/prepare-cloud-init.sh << 'EOF'
[content above]
EOF
chmod +x /Users/clint/code/clintecker/clanker-radio/deploy/prepare-cloud-init.sh
```

Expected: Cloud-init preparation script created

**Step 3: Create cloud-init network configuration**

Create file `./deploy/cloud-init-network-config.yaml`:
```yaml
version: 2
ethernets:
  ens18:
    dhcp4: true
    dhcp6: false
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/cloud-init-network-config.yaml << 'EOF'
version: 2
ethernets:
  ens18:
    dhcp4: true
    dhcp6: false
EOF
```

Expected: Cloud-init network config created

**Step 3: Create Proxmox VM creation script**

Create file `./deploy/proxmox-create-vm.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Proxmox VM Creation Script
# Creates a VM on proxmox-chi using cloud-init template

# Configuration
PROXMOX_HOST="${PROXMOX_HOST:-proxmox-chi}"
PROXMOX_NODE="${PROXMOX_NODE:-proxmox-chi}"
VM_ID="${VM_ID:-9000}"
VM_NAME="ai-radio-1"
VM_MEMORY=4096  # 4GB RAM
VM_CORES=2
VM_DISK_SIZE=100G  # Increased to accommodate music library (~1000 tracks + breaks + logs)
TEMPLATE_NAME="${TEMPLATE_NAME:-ubuntu-22.04-cloud}"
STORAGE="${STORAGE:-local-lvm}"
BRIDGE="${BRIDGE:-vmbr0}"

# Cloud-init files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_DATA="$SCRIPT_DIR/cloud-init-user-data.yaml"
NETWORK_CONFIG="$SCRIPT_DIR/cloud-init-network-config.yaml"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

# Check prerequisites
if [ ! -f "$USER_DATA" ]; then
    error "Cloud-init user-data not found: $USER_DATA"
fi

if [ ! -f "$NETWORK_CONFIG" ]; then
    error "Cloud-init network config not found: $NETWORK_CONFIG"
fi

# Check if cloud-init has been prepared
if [ ! -f "$USER_DATA" ]; then
    error "Cloud-init user-data not found. Run: $SCRIPT_DIR/prepare-cloud-init.sh"
fi

# Check if SSH key placeholder still exists (shouldn't if prepared correctly)
if grep -q '\${SSH_PUBLIC_KEY}' "$USER_DATA"; then
    error "Cloud-init not prepared. Run: $SCRIPT_DIR/prepare-cloud-init.sh"
fi

log "=== AI Radio Station VM Creation ==="
log "Proxmox Host: $PROXMOX_HOST"
log "VM ID: $VM_ID"
log "VM Name: $VM_NAME"
log "Memory: ${VM_MEMORY}MB"
log "Cores: $VM_CORES"
log "Disk: $VM_DISK_SIZE"

# Note: This script should be run ON the Proxmox host or via SSH
# For now, it outputs the commands to run manually

cat << PROXMOX_COMMANDS

Run these commands on Proxmox host '$PROXMOX_HOST':

# 0. Find your template ID (look for your Ubuntu cloud image template)
qm list | grep -i template
# Or list all templates:
pvesh get /cluster/resources --type vm | jq '.[] | select(.template==1)'

# 1. Clone template to new VM (replace <TEMPLATE_ID> with ID from step 0)
qm clone <TEMPLATE_ID> $VM_ID --name $VM_NAME --full

# 2. Configure VM resources
qm set $VM_ID --memory $VM_MEMORY --cores $VM_CORES --cpu host
qm set $VM_ID --net0 virtio,bridge=$BRIDGE

# 3. Resize disk
qm resize $VM_ID scsi0 $VM_DISK_SIZE

# 4. Set cloud-init configuration
# (Copy cloud-init files to Proxmox first)
qm set $VM_ID --cicustom "user=local:snippets/ai-radio-user-data.yaml,network=local:snippets/ai-radio-network-config.yaml"
qm set $VM_ID --ipconfig0 ip=dhcp

# 5. Set boot order
qm set $VM_ID --boot order=scsi0

# 6. Enable QEMU agent
qm set $VM_ID --agent enabled=1

# 7. Start VM
qm start $VM_ID

# 8. Get VM IP address (wait ~30 seconds for boot)
sleep 30
qm guest cmd $VM_ID network-get-interfaces | jq -r '.[] | select(.name == "ens18") | .["ip-addresses"][] | select(.["ip-address-type"] == "ipv4") | .["ip-address"]'

PROXMOX_COMMANDS

log ""
log "=== Manual Steps Required ==="
log "0. Prepare cloud-init with your SSH key:"
log "   ./deploy/prepare-cloud-init.sh"
log ""
log "1. Copy cloud-init files to Proxmox:"
log "   scp $USER_DATA root@$PROXMOX_HOST:/var/lib/vz/snippets/ai-radio-user-data.yaml"
log "   scp $NETWORK_CONFIG root@$PROXMOX_HOST:/var/lib/vz/snippets/ai-radio-network-config.yaml"
log ""
log "2. Run the commands above on Proxmox (after finding template ID)"
log ""
log "3. Once VM is running, proceed to Task 2 (Tailscale setup)"

```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/proxmox-create-vm.sh << 'EOF'
[content above]
EOF
chmod +x /Users/clint/code/clintecker/clanker-radio/deploy/proxmox-create-vm.sh
```

Expected: Proxmox VM creation script created and executable

**Step 4: Prepare cloud-init configuration with SSH key**

Run:
```bash
cd /Users/clint/code/clintecker/clanker-radio
./deploy/prepare-cloud-init.sh
```

Expected output:
```
[2025-12-18 10:00:00] Using SSH key from: /Users/clint/.ssh/id_ed25519.pub
[2025-12-18 10:00:00] Generating cloud-init configuration...
[2025-12-18 10:00:00] Cloud-init configuration ready: ./deploy/cloud-init-user-data.yaml
[2025-12-18 10:00:00]
[2025-12-18 10:00:00] Next step: Copy to Proxmox and create VM
```

This script automatically:
- Finds your SSH public key (id_ed25519.pub or id_rsa.pub)
- Uses `envsubst` to inject it into the template
- Creates the final `cloud-init-user-data.yaml` file

**Note:** If you have a non-standard SSH key location, set the environment variable:
```bash
SSH_KEY_FILE=/path/to/your/key.pub ./deploy/prepare-cloud-init.sh
```

---

## Task 2: Tailscale Installation & Configuration

**Files:**
- Create: `./deploy/tailscale-install.sh`

**Step 1: Create Tailscale installation script**

Create file `./deploy/tailscale-install.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Tailscale Installation & Configuration
# Provides secure administrative access to the VM

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

log "=== Tailscale Installation Started ==="

# Install Tailscale
if ! command -v tailscale &> /dev/null; then
    log "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh

    if [ $? -ne 0 ]; then
        error "Failed to install Tailscale"
    fi

    log "Tailscale installed successfully"
else
    log "Tailscale already installed ($(tailscale version))"
fi

# Check if already authenticated
if tailscale status --json 2>/dev/null | jq -e '.BackendState == "Running"' > /dev/null; then
    log "Tailscale is already authenticated and running"
    tailscale status
else
    log ""
    log "=== Tailscale Authentication Required ==="
    log ""
    log "Run ONE of the following commands to authenticate:"
    log ""
    log "Option 1 - Interactive (recommended for first setup):"
    log "  sudo tailscale up --hostname=ai-radio-1 --accept-routes"
    log ""
    log "Option 2 - With auth key (for automation):"
    log "  sudo tailscale up --authkey=tskey-auth-XXXXX --hostname=ai-radio-1 --accept-routes"
    log ""
    log "Get an auth key from: https://login.tailscale.com/admin/settings/keys"
    log ""
fi

# Enable Tailscale service
systemctl enable tailscaled || log "Warning: Could not enable tailscaled service"

log "=== Tailscale Installation Complete ==="
log ""
log "After authentication, you can access this VM via:"
log "  ssh clint@ai-radio-1"
log "  (or the Tailscale IP shown in 'tailscale status')"
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/tailscale-install.sh << 'EOF'
[content above]
EOF
chmod +x /Users/clint/code/clintecker/clanker-radio/deploy/tailscale-install.sh
```

Expected: Tailscale installation script created

**Step 2: Document Tailscale setup in deployment guide**

Create file `./deploy/README.md`:
```markdown
# AI Radio Station - Deployment Guide

## Phase -1: VM Provisioning on Proxmox

### Step 1: Prepare Cloud-Init Configuration

1. Edit `deploy/cloud-init-user-data.yaml`
2. Replace `REPLACE_WITH_YOUR_SSH_PUBLIC_KEY` with your actual SSH public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

### Step 2: Create VM on Proxmox

1. Copy cloud-init files to Proxmox:
   ```bash
   scp deploy/cloud-init-user-data.yaml root@proxmox-chi:/var/lib/vz/snippets/ai-radio-user-data.yaml
   scp deploy/cloud-init-network-config.yaml root@proxmox-chi:/var/lib/vz/snippets/ai-radio-network-config.yaml
   ```

2. Review and run commands from:
   ```bash
   ./deploy/proxmox-create-vm.sh
   ```

3. Wait for VM to boot (~30 seconds)

4. Get VM IP address from Proxmox UI or:
   ```bash
   ssh root@proxmox-chi "qm guest cmd 9000 network-get-interfaces"
   ```

### Step 3: Install Tailscale

1. SSH to the VM (use VM IP from Proxmox):
   ```bash
   ssh clint@<VM_IP>
   ```

2. Run Tailscale installation:
   ```bash
   sudo /srv/ai_radio/deploy/tailscale-install.sh
   ```

3. Authenticate Tailscale:
   ```bash
   sudo tailscale up --hostname=ai-radio-1 --accept-routes
   ```

4. Visit the authentication URL and approve the device

5. Verify Tailscale connection:
   ```bash
   tailscale status
   ```

### Step 4: Install Cloudflared Tunnel

1. Run Cloudflared installation:
   ```bash
   sudo /srv/ai_radio/deploy/cloudflared-install.sh
   ```

2. Authenticate with Cloudflare:
   ```bash
   sudo cloudflared tunnel login
   ```

3. Create tunnel:
   ```bash
   sudo cloudflared tunnel create ai-radio
   ```

4. Note the tunnel ID shown

5. Configure tunnel routing:
   ```bash
   sudo cloudflared tunnel route dns ai-radio radio.clintecker.com
   ```

6. Start tunnel service:
   ```bash
   sudo systemctl enable --now cloudflared
   ```

### Step 5: Bootstrap Application Deployment

1. Run bootstrap script:
   ```bash
   sudo /srv/ai_radio/deploy/bootstrap.sh
   ```

2. Verify repository cloned:
   ```bash
   ls -la /srv/ai_radio/
   ```

3. Proceed to Phase 0 (Foundation)

## Verification

After completing Phase -1, verify:

- ✅ VM is running on Proxmox
- ✅ Tailscale is connected (can SSH via `ai-radio-1` hostname)
- ✅ Cloudflared tunnel is active
- ✅ Repository is cloned to `/srv/ai_radio/`
- ✅ System information available: `ai-radio-info`

## Next Steps

Proceed to **Phase 0: Foundation** to set up directory structure, database, and Python environment.
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/README.md << 'EOF'
[content above]
EOF
```

Expected: Deployment README created

---

## Task 3: Cloudflared Tunnel Setup

**Files:**
- Create: `./deploy/cloudflared-install.sh`
- Create: `./deploy/cloudflared-config-template.yaml`

**Step 1: Create Cloudflared installation script**

Create file `./deploy/cloudflared-install.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Cloudflared Tunnel Installation
# Exposes Icecast stream publicly at radio.clintecker.com

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    log "ERROR: $*"
    exit 1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

log "=== Cloudflared Installation Started ==="

# Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    log "Installing cloudflared..."

    # Download latest cloudflared
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

    # Install package
    dpkg -i cloudflared-linux-amd64.deb

    if [ $? -ne 0 ]; then
        error "Failed to install cloudflared"
    fi

    # Cleanup
    rm cloudflared-linux-amd64.deb

    log "Cloudflared installed successfully"
else
    log "Cloudflared already installed ($(cloudflared --version))"
fi

# Check authentication status
if [ -f /root/.cloudflared/cert.pem ]; then
    log "Cloudflared is already authenticated"
    log ""
    log "Existing tunnels:"
    cloudflared tunnel list || log "  (none or error listing)"
else
    log ""
    log "=== Cloudflared Authentication Required ==="
    log ""
    log "1. Authenticate with Cloudflare:"
    log "   sudo cloudflared tunnel login"
    log ""
    log "2. Create a tunnel:"
    log "   sudo cloudflared tunnel create ai-radio"
    log ""
    log "3. Note the Tunnel ID displayed"
    log ""
    log "4. Configure the tunnel:"
    log "   sudo cp /srv/ai_radio/deploy/cloudflared-config-template.yaml /etc/cloudflared/config.yml"
    log "   sudo nano /etc/cloudflared/config.yml  # Update TUNNEL_ID and credentials path"
    log ""
    log "5. Route DNS to tunnel:"
    log "   sudo cloudflared tunnel route dns ai-radio radio.clintecker.com"
    log ""
    log "6. Install as systemd service:"
    log "   sudo cloudflared service install"
    log "   sudo systemctl enable --now cloudflared"
    log ""
fi

log "=== Cloudflared Installation Complete ==="
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/cloudflared-install.sh << 'EOF'
[content above]
EOF
chmod +x /Users/clint/code/clintecker/clanker-radio/deploy/cloudflared-install.sh
```

Expected: Cloudflared installation script created

**Step 2: Create Cloudflared configuration template**

Create file `./deploy/cloudflared-config-template.yaml`:
```yaml
# AI Radio Station - Cloudflared Tunnel Configuration
# Route traffic from radio.clintecker.com to local Icecast server

# Replace TUNNEL_ID_HERE with your actual tunnel ID from:
#   cloudflared tunnel create ai-radio
tunnel: TUNNEL_ID_HERE

# Replace TUNNEL_ID_HERE in the credentials path as well
credentials-file: /root/.cloudflared/TUNNEL_ID_HERE.json

# Ingress rules - route all traffic to Icecast
ingress:
  # Main radio stream
  - hostname: radio.clintecker.com
    service: http://127.0.0.1:8000
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      tcpKeepAlive: 30s
      keepAliveTimeout: 90s

  # Catch-all rule (required by cloudflared)
  - service: http_status:404

# Logging
loglevel: info

# Metrics (optional, for monitoring)
metrics: 127.0.0.1:9090
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/cloudflared-config-template.yaml << 'EOF'
[content above]
EOF
```

Expected: Cloudflared config template created

---

## Task 4: Repository Bootstrap Script

**Files:**
- Create: `./deploy/bootstrap.sh`

**Step 1: Create bootstrap deployment script**

Create file `./deploy/bootstrap.sh`:
```bash
#!/bin/bash
set -euo pipefail

# AI Radio Station - Bootstrap Deployment Script
# Clones repository and prepares for Phase 0 execution

REPO_URL="${REPO_URL:-https://github.com/clintecker/clanker-radio.git}"
DEPLOY_DIR="/srv/ai_radio"
LOG_FILE="/var/log/ai-radio-bootstrap.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $*"
    exit 1
}

log "=== AI Radio Station Bootstrap Started ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root (use sudo)"
fi

# Update system packages
log "Updating system packages..."
apt-get update || error "Failed to update package lists"

# Install git if not present
if ! command -v git &> /dev/null; then
    log "Installing git..."
    apt-get install -y git || error "Failed to install git"
fi

# Clone or update repository
if [ -d "$DEPLOY_DIR/.git" ]; then
    log "Repository already exists at $DEPLOY_DIR, pulling latest..."
    cd "$DEPLOY_DIR"
    git pull || error "Failed to pull latest changes"
else
    log "Cloning repository to $DEPLOY_DIR..."
    git clone "$REPO_URL" "$DEPLOY_DIR" || error "Failed to clone repository"
fi

# Verify critical files exist
CRITICAL_FILES=(
    "$DEPLOY_DIR/docs/plans"
    "$DEPLOY_DIR/deploy"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -e "$file" ]; then
        error "Critical path missing: $file"
    fi
done

log "Repository structure verified"

# Set basic permissions (full setup happens in Phase 0)
if id "ai-radio" &>/dev/null; then
    log "User ai-radio already exists"
else
    log "User ai-radio will be created in Phase 0"
fi

# Create quick status script
cat > /usr/local/bin/ai-radio-status << 'STATUS_SCRIPT'
#!/bin/bash
echo "=== AI Radio Station Status ==="
echo ""
echo "Phase -1: VM Provisioning"
echo "  ✅ VM provisioned on Proxmox"
echo "  ✅ Repository cloned to /srv/ai_radio"

if command -v tailscale &> /dev/null && tailscale status &> /dev/null; then
    echo "  ✅ Tailscale connected"
else
    echo "  ⚠️  Tailscale not configured"
fi

if systemctl is-active cloudflared &> /dev/null; then
    echo "  ✅ Cloudflared tunnel active"
else
    echo "  ⚠️  Cloudflared not configured"
fi

echo ""
echo "Next Steps:"
if [ ! -f /srv/ai_radio/db/radio.sqlite3 ]; then
    echo "  → Execute Phase 0 (Foundation)"
    echo "    cd /srv/ai_radio"
    echo "    # Follow docs/plans/2025-12-18-phase-0-foundation.md"
else
    echo "  → Phase 0 appears complete"
    echo "  → Check phase completion: ls -la /srv/ai_radio/"
fi
echo ""
STATUS_SCRIPT

chmod +x /usr/local/bin/ai-radio-status

log ""
log "=== AI Radio Station Bootstrap Complete ==="
log ""
log "Repository location: $DEPLOY_DIR"
log "Phase plans: $DEPLOY_DIR/docs/plans/"
log "Deployment scripts: $DEPLOY_DIR/deploy/"
log ""
log "Check status: ai-radio-status"
log ""
log "Next Step: Execute Phase 0 (Foundation)"
log "  1. Review: $DEPLOY_DIR/docs/plans/2025-12-18-phase-0-foundation.md"
log "  2. Begin executing tasks from the plan"
log ""
```

Run:
```bash
cat > /Users/clint/code/clintecker/clanker-radio/deploy/bootstrap.sh << 'EOF'
[content above]
EOF
chmod +x /Users/clint/code/clintecker/clanker-radio/deploy/bootstrap.sh
```

Expected: Bootstrap script created and executable

---

## Definition of Done

Phase -1 is complete when:

- ✅ VM created on proxmox-chi from cloud-init template
- ✅ Cloud-init configured with CLiNT's SSH key
- ✅ VM boots successfully with proper timezone (America/Chicago)
- ✅ Tailscale installed and authenticated
- ✅ Can SSH to VM via Tailscale hostname (`ssh clint@ai-radio-1`)
- ✅ Cloudflared tunnel installed and configured
- ✅ DNS route created: radio.clintecker.com → tunnel
- ✅ Repository cloned to `/srv/ai_radio/`
- ✅ Bootstrap verification script works (`ai-radio-status`)

## SOW Compliance Checklist

- ✅ Infrastructure provisioning (Proxmox VM)
- ✅ Secure access (Tailscale)
- ✅ Public access (Cloudflared tunnel to radio.clintecker.com)
- ✅ Deployment automation (bootstrap script)
- ✅ Section 7: Timezone configured (America/Chicago)

## Validation Notes

**Security Considerations:**
- SSH key-based authentication only (no password auth)
- Tailscale provides zero-trust network access
- Cloudflared tunnel removes need for exposed ports
- VM runs with minimal attack surface

**Deployment Automation:**
- Cloud-init handles initial provisioning
- Bootstrap script enables repeatable deployments
- All scripts are idempotent (safe to re-run)

**Next Phase Dependencies:**
- Phase 0 requires: VM running, repository cloned, sudo access
- Phase 0 will create: ai-radio user, directory structure, database

## Next Phase

Proceed to **Phase 0: Foundation** (currently Phase 0 in existing plans - will be renumbered to Phase 1)
