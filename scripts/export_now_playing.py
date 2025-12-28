#!/usr/bin/env python3
"""Export current/recent/upcoming tracks to static JSON for external clients.

Runs periodically via systemd timer to provide cached stream status.

Architecture:
- Icecast: Source of truth for what's CURRENTLY playing (real-time state)
- play_history: Historical log of START events (analytics)
- Liquidsoap socket: Queue queries for NEXT tracks (future state)
"""

import json
import logging
import os
import socket
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for ai_radio imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ai_radio.config import config

try:
    import requests
except ImportError:
    # Fallback if requests not available
    import urllib.request
    requests = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Use configuration paths
SOCKET_PATH = str(config.liquidsoap_sock_path)
OUTPUT_PATH = config.public_path / "now_playing.json"
DB_PATH = config.db_path


def query_socket(sock: socket.socket, command: str) -> str:
    """Send command to connected Liquidsoap socket and read full response."""
    try:
        sock.sendall(f"{command}\n".encode())

        # Buffer until we see END terminator (with CRLF or LF)
        buffer = b""
        while not (buffer.endswith(b"END\r\n") or buffer.endswith(b"END\n")):
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("Socket closed unexpectedly")
            buffer += chunk

        # Strip END marker (handle both CRLF and LF) and decode
        response = buffer.decode('utf-8', errors='ignore')
        response = response.removesuffix("END\r\n").removesuffix("END\n").strip()
        return response

    except Exception as e:
        logger.warning(f"Socket query '{command}' failed: {e}")
        return ""


def get_queue_next(limit: int = 1) -> list[dict]:
    """Get next N tracks from queues, checking priority order (breaks before music).

    Follows Liquidsoap fallback chain priority:
    1. override queue (operator control)
    2. break queue (news breaks, station IDs)
    3. music queue (songs)
    """
    try:
        # Use context manager to ensure socket cleanup
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(15.0)  # Increased timeout for metadata queries
            sock.connect(SOCKET_PATH)

            # Check queues in priority order (matching radio.liq fallback chain)
            # Skip override queue (operator-only, rarely used)
            for queue_name, source_type in [("breaks", "break"), ("music", "music")]:
                queue_ids = query_socket(sock, f"{queue_name}.queue")
                if not queue_ids:
                    continue  # Try next queue

                # Parse space-separated request IDs
                rids = queue_ids.split()[:limit]

                tracks = []
                for rid in rids:
                    # Get metadata for this request (reusing same socket)
                    metadata = query_socket(sock, f"request.metadata {rid}")
                    if not metadata:
                        continue

                    # Parse metadata lines (key="value" format)
                    meta_dict = {}
                    for line in metadata.split('\n'):
                        if '=' in line:
                            key, _, value = line.partition('=')
                            # Strip quotes from value
                            value = value.strip('"')
                            meta_dict[key] = value

                    if meta_dict:
                        filename = meta_dict.get("filename", "")

                        # Determine source type and override metadata for consistency
                        if source_type == "break":
                            if "/bumpers/" in filename or "station_id" in filename:
                                actual_source = "bumper"
                                title = "Station Identification"
                                artist = config.station_name
                            else:
                                actual_source = "break"
                                title = "News Break"
                                artist = config.station_name
                            asset_id = None
                            album = None
                        else:
                            # Music tracks - look up full metadata from database
                            actual_source = source_type
                            title = meta_dict.get("title", "Unknown")
                            # Always use "Clint Ecker" for music tracks
                            artist = "Clint Ecker"

                            # Look up asset_id and album from database
                            asset_id = None
                            album = None
                            try:
                                with sqlite3.connect(config.db_path) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "SELECT id, album FROM assets WHERE path = ?",
                                        (filename,)
                                    )
                                    row = cursor.fetchone()
                                    if row:
                                        asset_id = row[0]
                                        album = row[1]
                            except Exception as e:
                                logger.debug(f"Could not look up asset metadata for {filename}: {e}")

                        # Get duration from database or file
                        duration_sec = None

                        # Try Liquidsoap metadata first
                        if "duration" in meta_dict:
                            try:
                                duration_sec = float(meta_dict["duration"])
                            except (ValueError, TypeError):
                                pass

                        # If not available, look up from database
                        if duration_sec is None:
                            if actual_source == "music":
                                # Music tracks: query database
                                try:
                                    # Extract hash from filename (last path component without extension)
                                    asset_id_lookup = os.path.splitext(os.path.basename(filename))[0]

                                    # Quick database lookup for duration
                                    with sqlite3.connect(config.db_path) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("SELECT duration_sec FROM assets WHERE id = ?", (asset_id_lookup,))
                                        row = cursor.fetchone()
                                        if row and row[0]:
                                            duration_sec = row[0]
                                except Exception as e:
                                    logger.debug(f"Could not look up duration for {filename}: {e}")
                            # Note: breaks/bumpers may not have duration in queue
                            # This is acceptable for "next up" display

                        tracks.append({
                            "asset_id": asset_id,
                            "title": title,
                            "artist": artist,
                            "album": album,
                            "source": actual_source,
                            "duration_sec": duration_sec
                        })

                # If we found tracks in this queue, return them
                if tracks:
                    return tracks

            # No tracks found in any queue
            return []

    except (FileNotFoundError, ConnectionRefusedError, ConnectionError, socket.timeout) as e:
        logger.warning(f"Failed to get queue: {e}")
        return []




def get_recent_plays(limit: int = 5) -> list[dict]:
    """Get recent plays from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT
                ph.asset_id,
                COALESCE(a.title,
                    CASE
                        WHEN ph.source = 'break' THEN 'News Break'
                        WHEN ph.source = 'bumper' THEN 'Station ID'
                        ELSE 'Unknown'
                    END
                ) as title,
                COALESCE(a.artist, ?) as artist,
                a.album,
                a.duration_sec,
                a.path,
                ph.played_at,
                ph.source
            FROM play_history ph
            LEFT JOIN assets a ON ph.asset_id = a.id
            WHERE ph.source IN ('music', 'break', 'bumper')
            ORDER BY ph.played_at DESC
            LIMIT ?
            """,
            (config.station_name, limit)
        )

        rows = cursor.fetchall()
        conn.close()

        plays = []
        for row in rows:
            duration_sec = row[4]
            source = row[7]

            # For non-music tracks without duration: accept None
            # Expensive ffprobe removed - duration should be in database from ingestion
            # If missing, frontend will handle gracefully

            plays.append({
                "asset_id": row[0],
                "title": row[1] or "Unknown",
                "artist": row[2] or "Unknown",
                "album": row[3],
                "duration_sec": duration_sec,
                "played_at": row[6],
                "source": source
            })

        return plays

    except Exception as e:
        logger.warning(f"Failed to get recent plays: {e}")
        return []


def get_icecast_status() -> dict | None:
    """Get Icecast stream status including hidden mounts via admin endpoint.

    Returns:
        Dict with 'source' key containing list of mount dicts, or None if unavailable
    """
    try:
        import xml.etree.ElementTree as ET

        # Use admin stats endpoint to see hidden mounts
        # Admin credentials from config
        admin_url = f'{config.icecast_url}/admin/stats'

        if requests:
            response = requests.get(admin_url,
                                   auth=('admin', config.icecast_admin_password),
                                   timeout=3)
            xml_data = response.text
        else:
            # Fallback to urllib with basic auth
            import urllib.request
            import base64
            auth_str = base64.b64encode(f'admin:{config.icecast_admin_password}'.encode()).decode()
            req = urllib.request.Request(admin_url)
            req.add_header('Authorization', f'Basic {auth_str}')
            with urllib.request.urlopen(req, timeout=3) as response:
                xml_data = response.read().decode()

        # Parse XML response
        root = ET.fromstring(xml_data)

        # Extract source mounts
        sources = []
        for source_elem in root.findall('source'):
            mount = source_elem.get('mount')
            source_dict = {'listenurl': f'{config.icecast_url}{mount}'}

            # Extract relevant fields
            audio_info = None
            for child in source_elem:
                if child.tag in ['listeners', 'listener_peak', 'bitrate', 'samplerate', 'channels']:
                    try:
                        source_dict[child.tag] = int(child.text) if child.text else 0
                    except (ValueError, TypeError):
                        source_dict[child.tag] = 0
                elif child.tag == 'stream_start_iso8601':
                    source_dict['stream_start_iso8601'] = child.text
                elif child.tag == 'audio_info':
                    audio_info = child.text

            # Parse bitrate from audio_info if not directly available
            if 'bitrate' not in source_dict or source_dict['bitrate'] == 0:
                if audio_info:
                    # Parse "channels=2;samplerate=48000;bitrate=192"
                    for part in audio_info.split(';'):
                        if part.startswith('bitrate='):
                            try:
                                source_dict['bitrate'] = int(part.split('=')[1])
                            except (ValueError, IndexError):
                                pass

            sources.append(source_dict)

        return {'source': sources}

    except Exception as e:
        logger.warning(f"Failed to get Icecast status: {e}")
        return None


def get_liquidsoap_metadata() -> dict | None:
    """Get current track metadata directly from Liquidsoap socket.

    This is more accurate than Icecast for short tracks (breaks/station IDs)
    because Liquidsoap knows what's playing in real-time.

    Returns:
        Dict with filename and metadata, or None if unavailable
    """
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(5.0)
            sock.connect(SOCKET_PATH)

            # Query for current playing metadata
            # The main output source is called "radio" in radio.liq
            metadata_raw = query_socket(sock, "radio.metadata")

            if not metadata_raw:
                return None

            # Parse metadata (key="value" format)
            meta_dict = {}
            for line in metadata_raw.split('\n'):
                if '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip('"')
                    meta_dict[key] = value

            filename = meta_dict.get("filename", "")
            if not filename:
                return None

            return {
                "filename": filename,
                "title": meta_dict.get("title", ""),
                "artist": meta_dict.get("artist", ""),
                "album": meta_dict.get("album", "")
            }

    except Exception as e:
        logger.debug(f"Could not get Liquidsoap metadata: {e}")
        return None


def get_stream_info() -> dict | None:
    """Get stream metrics from Icecast.

    Returns:
        Dict with listener counts, bitrate, and fallback status, or None if unavailable
    """
    try:
        icecast_data = get_icecast_status()
        if not icecast_data:
            return None

        source_raw = icecast_data.get('source', {})

        fallback_mode = False
        # Handle both single source (dict) and multiple sources (list)
        if isinstance(source_raw, list):
            # Multiple sources - find /radio mount (but NOT /radio-fallback)
            main_source = next(
                (s for s in source_raw
                 if '/radio' in s.get('listenurl', '') and '/radio-fallback' not in s.get('listenurl', '')),
                None
            )

            fallback_source = next(
                (s for s in source_raw if '/radio-fallback' in s.get('listenurl', '')),
                None
            )

            # Use fallback if:
            # 1. No main source found, OR
            # 2. Main source exists but has no listeners AND fallback has listeners
            if not main_source or (fallback_source and
                                  main_source.get('listeners', 0) == 0 and
                                  fallback_source.get('listeners', 0) > 0):
                source_data = fallback_source if fallback_source else {}
                fallback_mode = True
            else:
                source_data = main_source
        else:
            # Single source - check if it's the fallback mount
            source_data = source_raw
            if '/radio-fallback' in source_data.get('listenurl', ''):
                fallback_mode = True

        return {
            "listeners": source_data.get('listeners', 0),
            "listener_peak": source_data.get('listener_peak', 0),
            "bitrate": source_data.get('bitrate', 0),
            "samplerate": source_data.get('samplerate', 0),
            "stream_start": source_data.get('stream_start_iso8601', None),
            "fallback_mode": fallback_mode
        }

    except Exception as e:
        logger.debug(f"Could not get stream info: {e}")
        return None


def get_current_playing() -> tuple[dict | None, dict | None]:
    """Get current track from play_history + assets JOIN.

    Simplified flow:
    1. Query play_history with LEFT JOIN to assets
    2. All metadata comes from database (no file inspection)
    3. Graceful degradation for deleted assets

    Returns:
        Tuple of (current_track, stream_info) or (None, None) if unavailable
    """
    from datetime import timedelta

    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()

    # Compute cutoff in Python for timestamp format compatibility
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    cursor.execute("""
        SELECT
            ph.asset_id,
            a.title,
            a.artist,
            a.album,
            a.duration_sec,
            ph.played_at,
            ph.source
        FROM play_history ph
        LEFT JOIN assets a ON ph.asset_id = a.id
        WHERE ph.played_at >= ?
        ORDER BY ph.played_at DESC
        LIMIT 1
    """, (cutoff,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, None

    # Graceful degradation for deleted assets
    if row[1] is None:  # title is NULL = deleted asset
        current = {
            "asset_id": row[0],
            "title": "[Deleted Track]",
            "artist": "Unknown",
            "album": None,
            "duration_sec": 0,
            "played_at": row[5],
            "source": row[6] if row[6] else "unknown"
        }
    else:
        current = {
            "asset_id": row[0],
            "title": row[1],
            "artist": row[2],
            "album": row[3],
            "duration_sec": row[4],
            "played_at": row[5],
            "source": row[6]
        }

    # Stream info from Icecast (keep existing logic)
    stream_info = get_stream_info()

    return current, stream_info


def export_now_playing():
    """Export current stream status to JSON file with atomic write."""
    try:
        # Get current track from Icecast (source of truth) + stream metrics
        current, stream_info = get_current_playing()

        # Get recent plays for history (excluding current if present)
        history = get_recent_plays(6)  # Get 6 to ensure we have 5 after filtering

        # If we have a current track, filter it out of history
        if current and current.get("asset_id"):
            history = [h for h in history if h.get("asset_id") != current["asset_id"]]

        # Limit history to 5 items
        history = history[:5]

        # Get next track from queue
        queue = get_queue_next(1)
        next_track = queue[0] if queue else None

        # Build output with stream info
        output = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stream": stream_info if stream_info else {},
            "current": current,
            "next": next_track,
            "history": history
        }

        # Ensure output directory exists
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: create temp file in same directory, then rename
        # This prevents concurrent writes and partial reads
        temp_dir = str(OUTPUT_PATH.parent)
        fd, temp_path = tempfile.mkstemp(dir=temp_dir, suffix='.json', text=True)

        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(output, f, indent=2)

            # Atomic rename (POSIX systems)
            os.rename(temp_path, str(OUTPUT_PATH))

            # Set permissions so nginx can read the file
            os.chmod(str(OUTPUT_PATH), 0o644)

            logger.info(f"Exported now_playing.json: current={current['title'] if current else 'None'}")
            return True

        except Exception as e:
            # Clean up temp file on error
            os.unlink(temp_path)
            raise

    except Exception as e:
        logger.error(f"Failed to export now_playing: {e}")
        return False


def main():
    """Entry point with lock to prevent simultaneous exports."""
    import fcntl

    lock_file_path = "/tmp/export_now_playing.lock"

    try:
        # Try to acquire exclusive lock (non-blocking)
        lock_file = open(lock_file_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # We got the lock - proceed with export
        success = export_now_playing()

        # Release lock
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

        sys.exit(0 if success else 1)

    except (IOError, OSError):
        # Lock already held - another export is running
        logger.debug("Export already in progress, exiting")
        sys.exit(0)  # Not an error, just skip this run


if __name__ == "__main__":
    main()
