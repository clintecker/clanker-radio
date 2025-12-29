#!/usr/bin/env python3
"""SSE Push Daemon - Watches now_playing.json and pushes updates to clients.

Eliminates polling latency and browser tab throttling by maintaining persistent
connections and pushing updates immediately when the file changes.
"""
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Set

from aiohttp import web
from watchfiles import awatch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# File to watch
NOW_PLAYING_PATH = config.paths.public_path / "now_playing.json"

# Connected clients (WebSocketResponse objects)
clients: Set[web.StreamResponse] = set()


async def sse_handler(request: web.Request) -> web.StreamResponse:
    """SSE endpoint - keeps connection open and pushes updates."""
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Connection"] = "keep-alive"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-Accel-Buffering"] = "no"  # Disable nginx buffering

    await response.prepare(request)

    # Add to connected clients
    clients.add(response)
    logger.info(f"Client connected. Total clients: {len(clients)}")

    try:
        # Send current state immediately
        if NOW_PLAYING_PATH.exists():
            data = NOW_PLAYING_PATH.read_text()
            # Minify JSON (remove newlines) for SSE compatibility
            data_compact = json.loads(data)
            data_str = json.dumps(data_compact, separators=(',', ':'))
            await response.write(f"data: {data_str}\n\n".encode())

        # Keep connection alive with periodic pings
        while True:
            await asyncio.sleep(30)  # Send keepalive every 30 seconds
            await response.write(": keepalive\n\n".encode())

    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        clients.discard(response)
        logger.info(f"Client disconnected. Total clients: {len(clients)}")

    return response


async def broadcast_update(data: str):
    """Broadcast update to all connected clients."""
    if not clients:
        return

    logger.info(f"Broadcasting update to {len(clients)} clients")

    # Minify JSON (remove newlines) for SSE compatibility
    data_compact = json.loads(data)
    data_str = json.dumps(data_compact, separators=(',', ':'))
    message = f"data: {data_str}\n\n".encode()

    # Send to all clients, remove disconnected ones
    disconnected = set()
    for client in clients:
        try:
            await client.write(message)
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            disconnected.add(client)

    # Clean up disconnected clients
    for client in disconnected:
        clients.discard(client)


async def watch_file():
    """Watch now_playing.json and broadcast updates."""
    watch_dir = NOW_PLAYING_PATH.parent
    target_file = NOW_PLAYING_PATH.name

    logger.info(f"Watching {watch_dir} for changes to {target_file}")

    async for changes in awatch(watch_dir):
        # Filter for changes to our specific file
        relevant_changes = [
            (change_type, path) for change_type, path in changes
            if Path(path).name == target_file
        ]

        if not relevant_changes:
            continue

        logger.debug(f"File changed: {relevant_changes}")

        try:
            data = NOW_PLAYING_PATH.read_text()
            await broadcast_update(data)
        except Exception as e:
            logger.error(f"Error reading/broadcasting file: {e}")


async def init_app() -> web.Application:
    """Initialize the web application."""
    app = web.Application()
    app.router.add_get("/stream", sse_handler)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))

    # Start file watcher as background task
    app["watcher_task"] = asyncio.create_task(watch_file())

    return app


async def cleanup(app: web.Application):
    """Cleanup on shutdown."""
    logger.info("Shutting down...")

    # Cancel watcher task
    if "watcher_task" in app:
        app["watcher_task"].cancel()
        try:
            await app["watcher_task"]
        except asyncio.CancelledError:
            pass

    # Close all client connections
    for client in list(clients):
        try:
            await client.write(b"event: close\ndata: Server shutting down\n\n")
        except:
            pass

    clients.clear()


def main():
    """Entry point."""
    # Check if file exists
    if not NOW_PLAYING_PATH.exists():
        logger.error(f"File not found: {NOW_PLAYING_PATH}")
        sys.exit(1)

    # Create app
    app = asyncio.run(init_app())
    app.on_cleanup.append(cleanup)

    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run server
    try:
        logger.info("Starting SSE push daemon on port 8001")
        web.run_app(app, host="127.0.0.1", port=8001, access_log=None)
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
