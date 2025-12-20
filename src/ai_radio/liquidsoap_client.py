"""
AI Radio Station - Liquidsoap Unix Socket Client
Communicates with Liquidsoap for queue management
"""
import logging
import socket
import re
from pathlib import Path

logger = logging.getLogger(__name__)

LIQUIDSOAP_SOCKET = Path("/run/liquidsoap/radio.sock")


class LiquidsoapClient:
    """Client for communicating with Liquidsoap via Unix socket"""

    def __init__(self, socket_path: Path = LIQUIDSOAP_SOCKET):
        self.socket_path = socket_path

    def send_command(self, command: str, timeout: float = 5.0) -> str:
        """
        Send command to Liquidsoap and return response

        Args:
            command: Liquidsoap command
            timeout: Socket timeout in seconds

        Returns:
            Response string from Liquidsoap

        Raises:
            ConnectionError: If cannot connect to socket
        """
        if not self.socket_path.exists():
            raise ConnectionError(f"Liquidsoap socket not found: {self.socket_path}")

        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect(str(self.socket_path))

            # Send command with newline
            sock.sendall(f"{command}\n".encode())

            # Read response (up to 64KB)
            response = sock.recv(65536).decode().strip()
            return response

        except socket.timeout:
            logger.error(f"Liquidsoap socket timeout after {timeout}s")
            raise ConnectionError("Liquidsoap socket timeout")

        except Exception as e:
            logger.error(f"Failed to communicate with Liquidsoap: {e}")
            raise ConnectionError(f"Liquidsoap communication error: {e}")

        finally:
            if sock:
                sock.close()

    def get_queue_length(self, queue_name: str) -> int:
        """
        Get current length of a queue

        Args:
            queue_name: Queue identifier (e.g., "music", "breaks")

        Returns:
            Number of items in queue
        """
        try:
            response = self.send_command(f"{queue_name}.queue")

            # Parse response - format is typically a list of items
            # Count non-empty lines (filter out Liquidsoap protocol END marker)
            lines = [
                line.strip()
                for line in response.split('\n')
                if line.strip() and line.strip() != "END"
            ]
            return len(lines)

        except ConnectionError as e:
            logger.error(f"Failed to get queue length: {e}")
            return -1

    def push_track(self, queue_name: str, file_path: Path | str) -> bool:
        """
        Push track to queue

        Args:
            queue_name: Queue identifier
            file_path: Path to audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.send_command(f"{queue_name}.push {file_path}")

            # Success if response doesn't contain "ERROR" or similar
            if "error" in response.lower():
                logger.error(f"Liquidsoap rejected push: {response}")
                return False

            logger.info(f"Pushed {file_path} to {queue_name} queue")
            return True

        except ConnectionError as e:
            logger.error(f"Failed to push track: {e}")
            return False

    def skip_current(self, queue_name: str) -> bool:
        """
        Skip currently playing track in queue

        Args:
            queue_name: Queue identifier

        Returns:
            True if successful
        """
        try:
            response = self.send_command(f"{queue_name}.skip")
            logger.info(f"Skipped current track in {queue_name}")
            return True

        except ConnectionError as e:
            logger.error(f"Failed to skip track: {e}")
            return False
