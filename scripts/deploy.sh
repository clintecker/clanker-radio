#!/bin/bash
# Deploy AI Radio Station files to production server
#
# Usage: ./scripts/deploy.sh [component]
#   component: frontend, scripts, systemd, code, config, all (default: all)

set -e

SERVER="clint@10.10.0.86"
BASE_REMOTE="/srv/ai_radio"
USER="clint"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}▶${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

deploy_frontend() {
    log_info "Deploying frontend..."
    scp nginx/index.html "${SERVER}:~/index.html" || { log_error "Failed to copy index.html"; exit 1; }

    if [ -f nginx/stream.m3u ]; then
        scp nginx/stream.m3u "${SERVER}:~/stream.m3u"
    fi

    ssh "${SERVER}" "sudo mv ~/index.html ${BASE_REMOTE}/public/ && \
                     sudo chmod 644 ${BASE_REMOTE}/public/index.html && \
                     sudo chown ${USER}:${USER} ${BASE_REMOTE}/public/index.html" || { log_error "Failed to install frontend"; exit 1; }

    if [ -f nginx/stream.m3u ]; then
        ssh "${SERVER}" "sudo mv ~/stream.m3u ${BASE_REMOTE}/public/ && \
                         sudo chmod 644 ${BASE_REMOTE}/public/stream.m3u && \
                         sudo chown ${USER}:${USER} ${BASE_REMOTE}/public/stream.m3u" || log_warn "Failed to install stream.m3u"
    fi

    log_success "Frontend deployed"
}

deploy_scripts() {
    log_info "Deploying Python scripts..."

    # Check if there are any Python scripts
    if ! ls scripts/*.py >/dev/null 2>&1; then
        log_warn "No Python scripts found to deploy"
        return 0
    fi

    # Copy all scripts and track filenames
    local script_files=()
    for script in scripts/*.py; do
        [ -f "$script" ] || continue
        local basename=$(basename "$script")
        scp "$script" "${SERVER}:~/${basename}" || { log_error "Failed to copy ${basename}"; exit 1; }
        script_files+=("${basename}")
    done

    # Move and set permissions for each file
    for script_file in "${script_files[@]}"; do
        ssh "${SERVER}" "sudo mv ~/${script_file} ${BASE_REMOTE}/scripts/${script_file} && \
                         sudo chown ${USER}:${USER} ${BASE_REMOTE}/scripts/${script_file} && \
                         sudo chmod 755 ${BASE_REMOTE}/scripts/${script_file}" || { log_error "Failed to install ${script_file}"; exit 1; }
    done

    log_success "Scripts deployed (${#script_files[@]} files)"
}

deploy_code() {
    log_info "Deploying Python package..."

    # Sync to temp directory
    rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' src/ai_radio/ "${SERVER}:~/ai_radio_tmp/" || { log_error "Failed to sync Python code"; exit 1; }

    # Install with correct permissions
    ssh "${SERVER}" "sudo rm -rf ${BASE_REMOTE}/src/ai_radio && \
                     sudo mv ~/ai_radio_tmp ${BASE_REMOTE}/src/ai_radio && \
                     sudo chown -R ${USER}:${USER} ${BASE_REMOTE}/src/ai_radio && \
                     sudo chmod -R 755 ${BASE_REMOTE}/src/ai_radio" || { log_error "Failed to install Python package"; exit 1; }

    log_success "Python package deployed"
}

deploy_config() {
    log_info "Deploying Liquidsoap config..."

    scp config/radio.liq "${SERVER}:~/radio.liq" || { log_error "Failed to copy radio.liq"; exit 1; }

    ssh "${SERVER}" "sudo mv ~/radio.liq ${BASE_REMOTE}/config/radio.liq && \
                     sudo chmod 644 ${BASE_REMOTE}/config/radio.liq && \
                     sudo chown ${USER}:${USER} ${BASE_REMOTE}/config/radio.liq" || { log_error "Failed to install config"; exit 1; }

    log_warn "Liquidsoap config updated - restart required"
    log_success "Config deployed"
}

deploy_systemd() {
    log_info "Deploying systemd units..."

    # Copy service files
    for unit in systemd/*.service systemd/*.timer; do
        [ -f "$unit" ] || continue
        scp "$unit" "${SERVER}:~/$(basename $unit)" || { log_error "Failed to copy $(basename $unit)"; exit 1; }
    done

    # Install and reload
    ssh "${SERVER}" "sudo mv ~/*.service ~/*.timer /etc/systemd/system/ 2>/dev/null || true && \
                     sudo systemctl daemon-reload" || { log_error "Failed to install systemd units"; exit 1; }

    log_success "Systemd units deployed (daemon reloaded)"
    log_warn "Services may need manual restart"
}

restart_services() {
    log_info "Restarting AI Radio services..."

    # Only restart if services are active
    ssh "${SERVER}" "sudo systemctl restart ai-radio-liquidsoap.service 2>/dev/null || true"

    log_success "Services restarted"
}

check_health() {
    log_info "Checking service health..."

    echo ""
    ssh "${SERVER}" "systemctl list-units 'ai-radio-*' --no-pager --no-legend" | while read -r line; do
        if echo "$line" | grep -q "failed"; then
            log_error "$line"
        elif echo "$line" | grep -q "running\|waiting"; then
            log_success "$line"
        else
            log_warn "$line"
        fi
    done
    echo ""
}

# Parse component argument
COMPONENT="${1:-all}"

case "$COMPONENT" in
    frontend)
        deploy_frontend
        ;;
    scripts)
        deploy_scripts
        ;;
    code)
        deploy_code
        ;;
    config)
        deploy_config
        read -p "Restart Liquidsoap? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ssh "${SERVER}" "sudo systemctl restart ai-radio-liquidsoap.service"
            log_success "Liquidsoap restarted"
        fi
        ;;
    systemd)
        deploy_systemd
        ;;
    all)
        deploy_frontend
        deploy_scripts
        deploy_code
        echo ""
        log_success "Deployment complete!"
        log_warn "Config and systemd units NOT deployed (use './scripts/deploy.sh config' or 'systemd' if needed)"
        echo ""
        check_health
        ;;
    health)
        check_health
        ;;
    *)
        echo "Usage: $0 [frontend|scripts|code|config|systemd|all|health]"
        echo ""
        echo "Components:"
        echo "  frontend - Deploy nginx/index.html and stream.m3u"
        echo "  scripts  - Deploy Python scripts"
        echo "  code     - Deploy Python package (src/ai_radio/)"
        echo "  config   - Deploy Liquidsoap config (prompts for restart)"
        echo "  systemd  - Deploy systemd units"
        echo "  all      - Deploy frontend + scripts + code (default)"
        echo "  health   - Check service health status"
        exit 1
        ;;
esac
