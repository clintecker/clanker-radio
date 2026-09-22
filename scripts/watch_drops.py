#!/usr/bin/env python3
"""AI Radio Station - Drop-in File Watchdog

Monitors /srv/ai_radio/drops/ for new MP3 files and automatically
pushes them to Liquidsoap's override queue via Unix socket.

When a file appears:
1. Wait for file size to stabilize (ensure file is fully written)
2. Push to override queue via socket command
3. Move file to processed/ directory
"""

import logging
import socket
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
DROPS_DIR = Path("/srv/ai_radio/drops")
PROCESSED_DIR = DROPS_DIR / "processed"
SOCKET_PATH = "/run/liquidsoap/radio.sock"
SUPPORTED_FORMATS = {".mp3", ".flac", ".wav"}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


class DropInHandler(FileSystemEventHandler):
    """Handle file creation events in drops directory."""

    def on_created(self, event):
        """Process newly created files."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process supported audio formats
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            log.warning(f"Ignoring unsupported file: {file_path.name}")
            return

        # Wait for file to be fully written (check size stability)
        if not self.wait_for_file_stability(file_path):
            return

        try:
            # Push to Liquidsoap override queue
            self.push_to_queue(file_path)

            # Move to processed directory
            processed_path = PROCESSED_DIR / file_path.name
            file_path.rename(processed_path)
            log.info(f"Moved to processed: {file_path.name}")

        except Exception as e:
            log.error(f"Failed to process {file_path.name}: {e}")

    def wait_for_file_stability(self, file_path: Path, timeout: int = 10) -> bool:
        """Wait for file size to stabilize before processing.

        Args:
            file_path: Path to the file to check
            timeout: Maximum seconds to wait

        Returns:
            True if file is stable, False if timeout or file disappeared
        """
        try:
            initial_size = -1
            start_time = time.time()

            while initial_size != file_path.stat().st_size:
                if time.time() - start_time > timeout:
                    log.warning(f"File size not stable after {timeout}s: {file_path.name}")
                    return False

                initial_size = file_path.stat().st_size
                time.sleep(0.2)  # Check every 200ms

            return True

        except FileNotFoundError:
            log.warning(f"File disappeared before processing: {file_path.name}")
            return False

    def push_to_queue(self, file_path: Path):
        """Push file to Liquidsoap override queue via Unix socket."""
        command = f"override.push {file_path}\n"

        try:
            # Connect to Liquidsoap Unix socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(SOCKET_PATH)

            # Send command
            sock.sendall(command.encode())

            # Read response
            response = sock.recv(1024).decode().strip()
            sock.close()

            log.info(f"Pushed to override queue: {file_path.name}")
            log.debug(f"Liquidsoap response: {response}")

        except Exception as e:
            raise RuntimeError(f"Socket communication failed: {e}")


def main():
    """Start watchdog monitoring."""
    log.info("Starting drop-in file watchdog")
    log.info(f"Monitoring: {DROPS_DIR}")
    log.info(f"Processed: {PROCESSED_DIR}")
    log.info(f"Socket: {SOCKET_PATH}")

    # Ensure processed directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Start monitoring
    event_handler = DropInHandler()
    observer = Observer()
    observer.schedule(event_handler, str(DROPS_DIR), recursive=False)
    observer.start()

    log.info("Watchdog running (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopping watchdog")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
