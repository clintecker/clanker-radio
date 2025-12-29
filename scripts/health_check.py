#!/usr/bin/env python3
"""Comprehensive health check for AI Radio Station.

Verifies all components are running correctly:
- Liquidsoap streaming engine
- Systemd timers and services
- Queue depths and track selection
- Icecast streaming
- Now playing metadata export
- Database connectivity

Usage:
    sudo -u ai-radio python3 health_check.py     # Run most checks
    sudo python3 health_check.py                  # Run all checks including systemd dependencies
"""
import json
import logging
import os
import random
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Use configuration paths
SOCKET_PATH = str(config.paths.liquidsoap_sock_path)
NOW_PLAYING_PATH = config.paths.public_path / "now_playing.json"

def print_header(text):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'=' * 70}{NC}")

def print_status(ok, message):
    """Print status line with color."""
    if ok:
        print(f"{GREEN}✓{NC} {message}")
    else:
        print(f"{RED}✗{NC} {message}")
    return ok

def query_liquidsoap(command: str, timeout: float = 5.0) -> str:
    """Query Liquidsoap socket."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(SOCKET_PATH)
            sock.sendall(f"{command}\n".encode())

            # Read until END marker
            buffer = b""
            while not (buffer.endswith(b"END\r\n") or buffer.endswith(b"END\n")):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk

            response = buffer.decode('utf-8', errors='ignore')
            response = response.removesuffix("END\r\n").removesuffix("END\n").strip()
            return response
    except Exception as e:
        logger.debug(f"Socket query failed: {e}")
        return ""

def check_liquidsoap_service():
    """Check Liquidsoap service status."""
    print_header("1. LIQUIDSOAP SERVICE")

    try:
        result = subprocess.run(
            ["systemctl", "is-active", "ai-radio-liquidsoap.service"],
            capture_output=True,
            text=True,
            timeout=5
        )

        is_active = result.stdout.strip() == "active"
        print_status(is_active, f"Service status: {result.stdout.strip()}")

        if is_active:
            # Get uptime
            result = subprocess.run(
                ["systemctl", "show", "ai-radio-liquidsoap.service", "--property=ActiveEnterTimestamp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"  {result.stdout.strip()}")

        return is_active

    except Exception as e:
        print_status(False, f"Failed to check service: {e}")
        return False

def check_timers():
    """Check all AI Radio timers are active."""
    print_header("2. SYSTEMD TIMERS")

    timers = [
        "ai-radio-enqueue.timer",
        "ai-radio-break-scheduler.timer",
        "ai-radio-schedule-station-id.timer",
        "ai-radio-export-nowplaying.timer",
        "ai-radio-break-gen.timer"
    ]

    all_ok = True

    for timer in timers:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", timer],
                capture_output=True,
                text=True,
                timeout=5
            )

            is_active = result.stdout.strip() == "active"
            all_ok = all_ok and is_active

            status = result.stdout.strip()
            print_status(is_active, f"{timer}: {status}")

        except Exception as e:
            print_status(False, f"{timer}: error - {e}")
            all_ok = False

    return all_ok

def check_queue_depths():
    """Check Liquidsoap queue depths."""
    print_header("3. QUEUE DEPTHS")

    if not Path(SOCKET_PATH).exists():
        print_status(False, "Liquidsoap socket not found")
        return False

    # Check music queue
    queue_response = query_liquidsoap("music.queue")
    if queue_response:
        # Queue IDs are returned as space-separated on a single line
        track_ids = [id for id in queue_response.split() if id.strip()]
        music_depth = len(track_ids)
        music_ok = music_depth >= 3  # MIN_QUEUE_DEPTH
        print_status(music_ok, f"Music queue: {music_depth} tracks (min: 3)")
    else:
        print_status(False, "Music queue: unable to query")
        music_ok = False

    # Check breaks queue
    breaks_response = query_liquidsoap("breaks.queue")
    if breaks_response:  # Fixed: query_liquidsoap returns "" on failure, not None
        # Queue IDs are returned as space-separated on a single line
        track_ids = [id for id in breaks_response.split() if id.strip()]
        breaks_depth = len(track_ids)
        print_status(True, f"Breaks queue: {breaks_depth} tracks")
    else:
        print_status(False, "Breaks queue: unable to query")

    return music_ok

def check_track_sensitive_config():
    """Verify track_sensitive=true is configured."""
    print_header("4. TRACK BOUNDARY PROTECTION")

    config_path = config.paths.base_path / "config" / "radio.liq"

    if not config_path.exists():
        print_status(False, "Config file not found")
        return False

    try:
        content = config_path.read_text()
        has_track_sensitive = "track_sensitive=true" in content

        print_status(
            has_track_sensitive,
            "track_sensitive=true in config (breaks wait for track finish)"
        )

        return has_track_sensitive

    except Exception as e:
        print_status(False, f"Failed to read config: {e}")
        return False

def check_icecast():
    """Check Icecast is streaming."""
    print_header("5. ICECAST STREAMING")

    try:
        import requests
        response = requests.get(f'{config.icecast_url}/status-json.xsl', timeout=3)
        data = response.json()

        icestats = data.get('icestats', {})
        source_data = icestats.get('source')

        # Handle both single mount (dict) and multiple mounts (list)
        if not source_data:
            print_status(False, "No active source")
            return False

        # Normalize to list for consistent handling
        sources = source_data if isinstance(source_data, list) else [source_data]

        # Look for our radio mount (first available source)
        if sources:
            source = sources[0]  # Use first mount
            listeners = source.get('listeners', 0)
            bitrate = source.get('bitrate', 0)

            print_status(True, f"Icecast is streaming")
            print(f"  Listeners: {listeners}")
            print(f"  Bitrate: {bitrate}")
            print(f"  Mount: {source.get('listenurl', 'unknown')}")
            return True
        else:
            print_status(False, "No active source")
            return False

    except Exception as e:
        print_status(False, f"Failed to connect to Icecast: {e}")
        return False

def check_now_playing():
    """Check now_playing.json is fresh."""
    print_header("6. NOW PLAYING METADATA")

    if not NOW_PLAYING_PATH.exists():
        print_status(False, "now_playing.json not found")
        return False

    try:
        # Check file age (use time.time() for consistency, no timezone issues)
        mtime = NOW_PLAYING_PATH.stat().st_mtime
        age_seconds = time.time() - mtime

        is_fresh = age_seconds < 30  # Should update every 10 seconds
        print_status(is_fresh, f"File age: {age_seconds:.1f} seconds (should be < 30s)")

        # Parse content
        data = json.loads(NOW_PLAYING_PATH.read_text())

        current = data.get('current')
        next_track = data.get('next')
        stream = data.get('stream', {})

        if current:
            print(f"  Current: {current.get('title')} by {current.get('artist')}")
            print(f"  Source: {current.get('source', 'unknown')}")
        else:
            print(f"  {YELLOW}⚠{NC} No current track")

        if next_track:
            print(f"  Next: {next_track.get('title')} by {next_track.get('artist')}")
        else:
            print(f"  {YELLOW}⚠{NC} No next track")

        print(f"  Stream listeners: {stream.get('listeners', 0)}")

        return is_fresh

    except Exception as e:
        print_status(False, f"Failed to parse now_playing.json: {e}")
        return False

def check_database():
    """Check database connectivity and track count."""
    print_header("7. DATABASE")

    try:
        conn = sqlite3.connect(config.paths.db_path)
        cursor = conn.cursor()

        # Check total music tracks
        cursor.execute("SELECT COUNT(*) FROM assets WHERE kind = 'music'")
        total_tracks = cursor.fetchone()[0]

        # Check valid file paths (sample for performance)
        cursor.execute("SELECT path FROM assets WHERE kind = 'music'")
        all_paths = [row[0] for row in cursor.fetchall()]

        # Sample up to 100 random paths to avoid expensive I/O
        sample_size = min(100, len(all_paths))
        paths_to_check = random.sample(all_paths, sample_size) if sample_size > 0 else []
        valid_count = sum(1 for p in paths_to_check if Path(p).exists())

        # Extrapolate to total (for display purposes)
        if sample_size > 0 and sample_size < len(all_paths):
            estimated_valid = int((valid_count / sample_size) * len(all_paths))
        else:
            estimated_valid = valid_count

        # Check recent plays
        cursor.execute("""
            SELECT COUNT(*) FROM play_history
            WHERE played_at >= datetime('now', '-24 hours')
        """)
        recent_plays = cursor.fetchone()[0]

        conn.close()

        # Check passes if all sampled tracks are valid
        tracks_ok = total_tracks > 0 and valid_count == sample_size
        if sample_size < len(all_paths):
            print_status(tracks_ok, f"Music tracks: ~{estimated_valid}/{total_tracks} estimated valid (sampled {sample_size})")
        else:
            print_status(tracks_ok, f"Music tracks: {valid_count}/{total_tracks} with valid paths")
        print(f"  Plays in last 24h: {recent_plays}")

        return tracks_ok

    except Exception as e:
        print_status(False, f"Database error: {e}")
        return False

def check_disk_space():
    """Check available disk space on /srv/ai_radio partition."""
    print_header("8. DISK SPACE")

    try:
        # Get disk usage for the ai_radio directory
        usage = shutil.disk_usage(config.paths.base_path)

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        percent_used = (usage.used / usage.total) * 100

        # Warn if > 80% used, fail if > 90% used
        is_critical = percent_used > 90
        is_warning = percent_used > 80

        if is_critical:
            print_status(False, f"Disk space critical: {percent_used:.1f}% used ({free_gb:.1f} GB free)")
        elif is_warning:
            print_status(True, f"Disk space warning: {percent_used:.1f}% used ({free_gb:.1f} GB free)")
            print(f"  {YELLOW}⚠{NC} Consider freeing up space")
        else:
            print_status(True, f"Disk space: {percent_used:.1f}% used ({free_gb:.1f} GB free)")

        print(f"  Total: {total_gb:.1f} GB, Used: {used_gb:.1f} GB")

        return not is_critical

    except Exception as e:
        print_status(False, f"Failed to check disk space: {e}")
        return False

def check_track_selection():
    """Test track selection logic."""
    print_header("9. TRACK SELECTION")

    try:
        conn = sqlite3.connect(config.paths.db_path)
        cursor = conn.cursor()

        # Get recently played
        cursor.execute("""
            SELECT asset_id FROM play_history
            ORDER BY played_at DESC
            LIMIT 20
        """)
        recent_ids = [row[0] for row in cursor.fetchall()]

        # Test selection query
        if recent_ids:
            placeholders = ','.join('?' * len(recent_ids))
            cursor.execute(f"""
                SELECT COUNT(*) FROM assets
                WHERE kind = 'music'
                  AND id NOT IN ({placeholders})
            """, recent_ids)
        else:
            cursor.execute("SELECT COUNT(*) FROM assets WHERE kind = 'music'")

        available = cursor.fetchone()[0]
        conn.close()

        selection_ok = available >= 5  # Should have at least TARGET_QUEUE_DEPTH available
        print_status(
            selection_ok,
            f"Available tracks after exclusions: {available} (need: 5+)"
        )

        if available < 20:
            print(f"  {YELLOW}⚠{NC} Limited track variety - consider adding more music")

        return selection_ok

    except Exception as e:
        print_status(False, f"Track selection check failed: {e}")
        return False

def check_recent_errors():
    """Check for recent errors in Liquidsoap logs."""
    print_header("10. RECENT ERRORS")

    try:
        result = subprocess.run(
            ["journalctl", "-u", "ai-radio-liquidsoap.service", "-n", "100", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Look for error patterns
        lines = result.stdout.split('\n')
        error_lines = [
            line for line in lines
            if any(pattern in line.lower() for pattern in ['error', 'failed', 'exception'])
            and 'Could not update timestamps' not in line  # Ignore benign ffmpeg warnings
        ]

        has_errors = len(error_lines) > 0

        if not has_errors:
            print_status(True, "No recent errors in logs")
        else:
            print_status(False, f"Found {len(error_lines)} error(s) in recent logs")
            for line in error_lines[-5:]:  # Show last 5
                print(f"  {line}")

        return not has_errors

    except Exception as e:
        print_status(False, f"Failed to check logs: {e}")
        return False

def check_service_dependencies():
    """Verify systemd service dependencies are correct."""
    print_header("11. SERVICE DEPENDENCIES")

    services = {
        "ai-radio-enqueue.service": "BindsTo=ai-radio-liquidsoap.service",
        "ai-radio-break-scheduler.service": "BindsTo=ai-radio-liquidsoap.service",
        "ai-radio-schedule-station-id.service": "BindsTo=ai-radio-liquidsoap.service",
        "ai-radio-export-nowplaying.service": "BindsTo=ai-radio-liquidsoap.service"
    }

    all_ok = True

    for service, expected_dep in services.items():
        try:
            result = subprocess.run(
                ["systemctl", "cat", service],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Check for permission errors
            if result.returncode != 0:
                if "Permission denied" in result.stderr:
                    print_status(False, f"{service}: Permission denied (run as root/sudo)")
                else:
                    print_status(False, f"{service}: systemctl error: {result.stderr.strip()}")
                all_ok = False
                continue

            has_correct_dep = expected_dep in result.stdout
            has_wrong_dep = "Requires=ai-radio-liquidsoap.service" in result.stdout

            if has_correct_dep and not has_wrong_dep:
                print_status(True, f"{service}: correct BindsTo dependency")
            elif has_wrong_dep:
                print_status(False, f"{service}: uses Requires= (should be BindsTo=)")
                all_ok = False
            else:
                print_status(False, f"{service}: missing dependency")
                all_ok = False

        except Exception as e:
            print_status(False, f"{service}: {e}")
            all_ok = False

    return all_ok

def main():
    """Run all health checks."""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}AI Radio Station - Health Check{NC}")
    print(f"{BLUE}{'=' * 70}{NC}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    checks = {
        "Liquidsoap Service": check_liquidsoap_service,
        "Systemd Timers": check_timers,
        "Queue Depths": check_queue_depths,
        "Track Boundary Protection": check_track_sensitive_config,
        "Icecast Streaming": check_icecast,
        "Now Playing Metadata": check_now_playing,
        "Database": check_database,
        "Disk Space": check_disk_space,
        "Track Selection": check_track_selection,
        "Recent Errors": check_recent_errors,
        "Service Dependencies": check_service_dependencies
    }

    results = {}
    for name, check_func in checks.items():
        try:
            results[name] = check_func()
        except Exception as e:
            logger.error(f"Check '{name}' crashed: {e}")
            results[name] = False

    # Summary
    print_header("HEALTH CHECK SUMMARY")

    passed = sum(1 for ok in results.values() if ok)
    total = len(results)

    for name, ok in results.items():
        status = f"{GREEN}PASS{NC}" if ok else f"{RED}FAIL{NC}"
        print(f"  {status}  {name}")

    print(f"\n{BLUE}{'=' * 70}{NC}")

    if passed == total:
        print(f"{GREEN}✓ ALL CHECKS PASSED ({passed}/{total}){NC}")
        print(f"{GREEN}Radio station is healthy!{NC}")
        return 0
    else:
        print(f"{YELLOW}⚠ {passed}/{total} CHECKS PASSED{NC}")
        print(f"{YELLOW}Some issues detected - review output above{NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
