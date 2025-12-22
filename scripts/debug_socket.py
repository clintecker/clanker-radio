#!/usr/bin/env python3
"""Debug script to trace socket communication timing."""

import socket
import time

SOCKET_PATH = "/run/liquidsoap/radio.sock"

def timed_query(command: str):
    """Query socket with detailed timing."""
    print(f"\n=== Query: {command} ===")

    start = time.time()

    try:
        # Connect
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(15.0)

        connect_start = time.time()
        sock.connect(SOCKET_PATH)
        print(f"[{time.time() - start:.3f}s] Connected to socket")

        # Send command
        send_start = time.time()
        sock.sendall(f"{command}\n".encode())
        print(f"[{time.time() - start:.3f}s] Sent command ({len(command)} bytes)")

        # Receive response
        recv_start = time.time()
        buffer = b""
        chunk_count = 0

        while not buffer.endswith(b"END\n"):
            chunk = sock.recv(4096)
            chunk_count += 1

            if not chunk:
                print(f"[{time.time() - start:.3f}s] Socket closed unexpectedly!")
                break

            buffer += chunk
            print(f"[{time.time() - start:.3f}s] Received chunk {chunk_count} ({len(chunk)} bytes, total: {len(buffer)})")

        response = buffer.decode('utf-8', errors='ignore').removesuffix("END\n").strip()
        print(f"[{time.time() - start:.3f}s] Complete response ({len(response)} chars)")
        print(f"Response: {response[:200]}{'...' if len(response) > 200 else ''}")

        sock.close()
        print(f"[{time.time() - start:.3f}s] Socket closed")

        return response

    except socket.timeout as e:
        print(f"[{time.time() - start:.3f}s] TIMEOUT: {e}")
        return None
    except Exception as e:
        print(f"[{time.time() - start:.3f}s] ERROR: {e}")
        return None

if __name__ == "__main__":
    # Test queries
    print("Testing Liquidsoap socket communication...")

    # Query 1: Get queue (should be fast)
    queue_result = timed_query("music.queue")

    if queue_result:
        # Query 2: Get metadata for first track
        rids = queue_result.split()
        if rids:
            first_rid = rids[0]
            timed_query(f"request.metadata {first_rid}")
