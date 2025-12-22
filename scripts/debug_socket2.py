#!/usr/bin/env python3
"""Debug script to see what data is actually received."""

import socket
import time

SOCKET_PATH = "/run/liquidsoap/radio.sock"

print("Testing socket communication...")

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(2.0)
sock.connect(SOCKET_PATH)

# Send command
sock.sendall(b"music.queue\n")
print("Sent: music.queue")

# Receive ALL data (don't wait for END)
buffer = b""
try:
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            print("Socket closed")
            break
        buffer += chunk
        print(f"Received chunk: {len(chunk)} bytes")
        print(f"Chunk repr: {chunk!r}")
        print(f"Total buffer: {len(buffer)} bytes")
        print(f"Buffer repr: {buffer!r}")
        end_marker = b'END\n'
        print(f"Buffer ends with END marker: {buffer.endswith(end_marker)}")
        print("---")

        if buffer.endswith(b"END\n"):
            print("Got END marker!")
            break

except socket.timeout:
    print(f"Timeout after {len(buffer)} bytes")
    print(f"Final buffer repr: {buffer!r}")
    print(f"Final buffer decoded: {buffer.decode('utf-8', errors='replace')}")

sock.close()
