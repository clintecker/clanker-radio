#!/usr/bin/env bash
set -euo pipefail

# AI Radio Station - Liquidsoap Wrapper Script
# Initializes OPAM environment, starts Liquidsoap, and immediately enqueues music

# OPAM Environment
export OPAM_SWITCH_PREFIX='/srv/ai_radio/.opam/5.2.0'
export CAML_LD_LIBRARY_PATH='/srv/ai_radio/.opam/5.2.0/lib/stublibs:/srv/ai_radio/.opam/5.2.0/lib/ocaml/stublibs:/srv/ai_radio/.opam/5.2.0/lib/ocaml'
export OCAML_TOPLEVEL_PATH='/srv/ai_radio/.opam/5.2.0/lib/toplevel'
export PATH="/srv/ai_radio/.opam/5.2.0/bin:$PATH"
export MANPATH=":/srv/ai_radio/.opam/5.2.0/man"

LIQUIDSOAP_BIN="/srv/ai_radio/.opam/5.2.0/bin/liquidsoap"
RADIO_CONFIG="/srv/ai_radio/config/radio.liq"
SOCKET_PATH="/run/liquidsoap/radio.sock"
VENV_PYTHON="/srv/ai_radio/.venv/bin/python"
ENQUEUE_SCRIPT="/srv/ai_radio/scripts/enqueue_music.py"

if [[ ! -x "${LIQUIDSOAP_BIN}" ]]; then
    echo "Error: Liquidsoap binary not found at ${LIQUIDSOAP_BIN}" >&2
    exit 1
fi

if [[ ! -f "${RADIO_CONFIG}" ]]; then
    echo "Error: Liquidsoap configuration not found at ${RADIO_CONFIG}" >&2
    exit 1
fi

# Start Liquidsoap in background
"${LIQUIDSOAP_BIN}" "${RADIO_CONFIG}" &
LIQUIDSOAP_PID=$!

# Wait for Liquidsoap socket to be ready (max 30 seconds)
# Check for actual connection readiness, not just file existence
echo "Waiting for Liquidsoap socket..."
SOCKET_READY=false
for i in {1..30}; do
    if [[ -S "${SOCKET_PATH}" ]]; then
        # Socket file exists, now test if it accepts connections
        if echo "help" | timeout 1 socat -t 1 - "${SOCKET_PATH}" &>/dev/null; then
            echo "Socket ready and accepting connections after ${i} seconds"
            SOCKET_READY=true
            break
        fi
    fi
    sleep 1
done

if [[ "${SOCKET_READY}" != "true" ]]; then
    echo "Warning: Socket not ready after 30 seconds, continuing anyway..." >&2
fi

# Enqueue music immediately (synchronously - wait for completion)
if [[ -x "${VENV_PYTHON}" ]] && [[ -f "${ENQUEUE_SCRIPT}" ]]; then
    echo "Enqueueing initial music..."
    "${VENV_PYTHON}" "${ENQUEUE_SCRIPT}"
    echo "Music enqueued successfully"
else
    echo "Warning: Could not enqueue music - python or script not found" >&2
fi

# Wait for Liquidsoap process (bring to foreground)
# Music is now enqueued and will start playing immediately
wait "${LIQUIDSOAP_PID}"
