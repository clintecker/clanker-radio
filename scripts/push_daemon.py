#!/usr/bin/env python3
"""SSE Push Daemon - Receives state updates and broadcasts to connected clients.

Eliminates polling latency and browser tab throttling by maintaining persistent
connections and pushing updates immediately via POST /notify endpoint.
No file I/O - full state is sent directly via HTTP.
"""
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Set, Optional

from aiohttp import web

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Connected clients (WebSocketResponse objects)
clients: Set[web.StreamResponse] = set()

# Last broadcasted state (sent to new clients immediately)
last_state: Optional[str] = None


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
        # Send current state immediately if we have it
        global last_state
        if last_state:
            # Minify JSON (remove newlines) for SSE compatibility
            data_compact = json.loads(last_state)
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
    """Broadcast update to all connected clients and store as last_state."""
    global last_state

    # Store this as the last state for new clients
    last_state = data

    if not clients:
        return

    # Log summary of what we're broadcasting
    try:
        state = json.loads(data)
        current_title = state.get('current', {}).get('title', 'None') if state.get('current') else 'None'
        next_title = state.get('next', {}).get('title', 'None') if state.get('next') else 'None'
        history_count = len(state.get('history', []))
        stream_info = state.get('stream', {})
        logger.info(f"Broadcasting to {len(clients)} clients: current={current_title}, next={next_title}, history={history_count} tracks, stream={stream_info.get('bitrate', 'N/A')}kbps")
    except:
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


async def notify_handler(request: web.Request) -> web.Response:
    """HTTP POST endpoint for receiving full state updates.

    Accepts JSON payload with current/next/history/stream data and broadcasts
    directly to SSE clients. No file I/O needed.
    """
    try:
        # Get JSON payload from request body
        data = await request.text()

        if not data:
            return web.Response(text="Empty payload", status=400)

        # Validate it's valid JSON
        try:
            json.loads(data)
        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON", status=400)

        # Broadcast to all connected clients
        await broadcast_update(data)
        return web.Response(text="OK")

    except Exception as e:
        logger.error(f"Error handling notify: {e}")
        return web.Response(text=f"Error: {e}", status=500)


async def fetch_initial_state():
    """Fetch initial state after server starts."""
    global last_state
    try:
        # Import the functions we need from export_now_playing
        sys.path.insert(0, str(Path(__file__).parent))
        from export_now_playing import get_current_playing, get_recent_plays, get_both_queues
        from datetime import datetime, timezone

        logger.info("Fetching initial state...")

        # Build state directly without POSTing to ourselves
        current, stream_info = get_current_playing()
        history = get_recent_plays(16)
        if current and current.get("asset_id"):
            history = [h for h in history if h.get("asset_id") != current["asset_id"]]
        history = history[:15]
        queues = get_both_queues(breaks_limit=3, music_limit=5)

        output = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "system_status": "online",
            "crossfade": {
                "music_sec": 4.0,    # Music tracks: 4s crossfade (2s fade-out + 2s fade-in)
                "breaks_sec": 0.0    # Breaks/station IDs: hard cut, no crossfade
            },
            "stream": stream_info if stream_info else {},
            "current": current,
            "breaks_queue": queues["breaks_queue"],
            "music_queue": queues["music_queue"],
            "history": history
        }

        # Store as last_state directly
        last_state = json.dumps(output)
        logger.info(f"Initial state loaded: current={current['title'] if current else 'None'}")
    except Exception as e:
        logger.warning(f"Could not fetch initial state: {e}")


async def init_app() -> web.Application:
    """Initialize the web application."""
    app = web.Application()
    app.router.add_get("/stream", sse_handler)
    app.router.add_post("/notify", notify_handler)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))

    # Schedule initial state fetch after server starts
    app.on_startup.append(lambda app: asyncio.create_task(fetch_initial_state()))

    return app


async def cleanup(app: web.Application):
    """Cleanup on shutdown."""
    logger.info("Shutting down...")

    # Send shutdown notification to all connected clients
    shutdown_message = {
        "system_status": "restarting",
        "message": "Push service restarting - reconnecting shortly..."
    }
    message_str = json.dumps(shutdown_message, separators=(',', ':'))
    shutdown_data = f"data: {message_str}\n\n".encode()

    for client in list(clients):
        try:
            await client.write(shutdown_data)
            await client.write(b"event: close\ndata: Server shutting down\n\n")
            await client.write_eof()
        except:
            pass
    clients.clear()


def main():
    """Entry point."""

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
