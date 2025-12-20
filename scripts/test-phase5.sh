#!/bin/bash
set -euo pipefail

echo "=== Phase 5: Scheduling & Orchestration Tests ==="
echo

# Test 1: Verify Liquidsoap client module
echo "[Test 1] Verify Liquidsoap client..."
if uv run python -c "from ai_radio.liquidsoap_client import LiquidsoapClient" 2>/dev/null; then
    echo "  ✓ Liquidsoap client module available"
else
    echo "  ✗ Liquidsoap client module missing"
    exit 1
fi

# Test 2: Verify track selection module
echo "[Test 2] Verify track selection module..."
if uv run python -c "from ai_radio.track_selection import select_next_tracks, build_energy_flow" 2>/dev/null; then
    echo "  ✓ Track selection module available"
else
    echo "  ✗ Track selection module missing"
    exit 1
fi

# Test 3: Verify enqueue script exists
echo "[Test 3] Verify enqueue script..."
if [ -x "scripts/enqueue_music.py" ]; then
    echo "  ✓ Enqueue script executable"
else
    echo "  ✗ Enqueue script missing or not executable"
    exit 1
fi

# Test 4: Verify break scheduler exists
echo "[Test 4] Verify break scheduler..."
if [ -x "scripts/schedule_break.py" ]; then
    echo "  ✓ Break scheduler executable"
else
    echo "  ✗ Break scheduler missing or not executable"
    exit 1
fi

# Test 5: Verify systemd unit files exist
echo "[Test 5] Verify systemd unit files..."
if [ -f "systemd/ai-radio-enqueue.service" ] && \
   [ -f "systemd/ai-radio-enqueue.timer" ] && \
   [ -f "systemd/ai-radio-break-scheduler.service" ] && \
   [ -f "systemd/ai-radio-break-scheduler.timer" ]; then
    echo "  ✓ All systemd unit files present"
else
    echo "  ✗ Systemd unit files missing"
    exit 1
fi

# Test 6: Run unit tests
echo "[Test 6] Run unit tests..."
if uv run pytest tests/test_liquidsoap_client.py tests/test_track_selection.py -v; then
    echo "  ✓ Unit tests passed"
else
    echo "  ✗ Unit tests failed"
    exit 1
fi

echo
echo "=== All Phase 5 Tests Passed ✓ ==="
