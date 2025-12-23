#!/usr/bin/env python3
"""Enqueue station ID bumper to music queue.

Periodically injects station IDs into the music queue for brand reinforcement.
Designed to run via systemd timer every 10 minutes.

Usage:
    ./scripts/enqueue_station_id.py

Exit codes:
    0: Station ID enqueued successfully
    1: Failed to enqueue station ID
"""

import logging
import random
import socket
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Use configuration paths
SOCKET_PATH = str(config.liquidsoap_sock_path)
BUMPERS_DIR = config.bumpers_path


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


def select_station_id() -> Path:
    """Select a random station ID from available files.

    Returns:
        Path to selected station ID file

    Note: Currently uses simple random selection. Future enhancement could
    track play history to avoid repeats within a time window.
    """
    # Get all station ID files (both WAV and MP3)
    all_station_ids = sorted(BUMPERS_DIR.glob("station_id_*.*"))

    if not all_station_ids:
        raise FileNotFoundError(f"No station IDs found in {BUMPERS_DIR}")

    logger.info(f"Found {len(all_station_ids)} station ID files")

    # Randomly select one
    # TODO: Check play history to avoid recent repeats once station IDs
    # are properly tracked as assets in the database
    selected = random.choice(all_station_ids)
    logger.info(f"Selected station ID: {selected.name}")

    return selected


def push_to_queue(file_path: Path) -> bool:
    """Push station ID to music queue via Liquidsoap socket.

    Clears the queue first so station ID plays immediately after current track.

    Args:
        file_path: Absolute path to station ID file

    Returns:
        True if successfully pushed, False otherwise
    """
    try:
        # Connect to Liquidsoap socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(5.0)
            sock.connect(SOCKET_PATH)

            # Push to breaks queue (plays at next track boundary)
            command = f"breaks.push {file_path}"
            response = query_socket(sock, command)

            if not response:
                logger.error("No response from Liquidsoap")
                return False

            # Response should be a request ID or error
            if response.isdigit():
                logger.info(f"Station ID queued successfully (request ID: {response})")
                return True
            else:
                logger.error(f"Unexpected response from Liquidsoap: {response}")
                return False

    except FileNotFoundError:
        logger.error(f"Liquidsoap socket not found: {SOCKET_PATH}")
        return False
    except ConnectionRefusedError:
        logger.error("Liquidsoap not running or socket not accessible")
        return False
    except socket.timeout:
        logger.error("Socket connection timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to push to queue: {e}")
        return False


def main() -> int:
    """Entry point for station ID enqueue service.

    Returns:
        0 if successful, 1 if failed
    """
    logger.info("Starting station ID enqueue service")

    try:
        # Select station ID
        station_id = select_station_id()

        # Push to queue
        if push_to_queue(station_id):
            logger.info(f"Successfully enqueued station ID: {station_id.name}")
            return 0
        else:
            logger.error("Failed to enqueue station ID")
            return 1

    except FileNotFoundError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
