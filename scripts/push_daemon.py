#!/usr/bin/env python3
"""SSE push daemon: owns now-playing state and broadcasts it to listeners.

Event flow (see docs/SSE_INTEGRATION_GUIDE.md):

    Liquidsoap (final on-air source) --POST /event--> this daemon --SSE /stream--> browsers

- POST /event   One track start from Liquidsoap: {rid, filename, kind, on_air_at, duration, title, artist}.
                Applied in on-air order, idempotent, recorded to play_history asynchronously.
- POST /notify  Legacy hook. Body is ignored: the daemon picks up any newer play that
                record_play.py wrote to sqlite, refreshes queues and rebroadcasts its own state.
- GET  /stream  Server-sent events. Every message is the full payload.
- GET  /state   The current payload as JSON (debugging / scripts).

Next-up comes from the Liquidsoap socket (after every event and every QUEUE_POLL_SEC),
stream stats from Icecast every STREAM_POLL_SEC. History survives restarts via sqlite.
"""
import asyncio
import json
import logging
import signal
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ai_radio.config import config  # noqa: E402
from ai_radio.now_playing import (  # noqa: E402
    NowPlayingState,
    TrackEvent,
    build_track,
    insert_play,
    load_recent,
    resolve_asset,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("push_daemon")

QUEUE_POLL_SEC = 15.0
STREAM_POLL_SEC = 10.0
KEEPALIVE_SEC = 30.0


def _station_name() -> str:
    try:
        return config.station.station_name
    except Exception:
        return "Last Byte Radio"


class Daemon:
    """All mutable daemon state. Blocking work (sqlite, socket, Icecast) runs in threads."""

    def __init__(self, db_path: Path, station_name: str, queue_fetcher=None, stream_fetcher=None):
        self.db_path = Path(db_path)
        self.station_name = station_name
        self.state = NowPlayingState()
        self.clients: Set[web.StreamResponse] = set()
        self.lock = asyncio.Lock()
        self.queue_fetcher = queue_fetcher
        self.stream_fetcher = stream_fetcher
        self._last_broadcast_key: Optional[str] = None
        self._tasks: list[asyncio.Task] = []

    # -- sqlite -----------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

    def load_history_sync(self) -> list[dict]:
        with self._connect() as conn:
            return load_recent(conn, self.station_name)

    def resolve_sync(self, event: TrackEvent) -> dict:
        try:
            with self._connect() as conn:
                asset = resolve_asset(conn, event.filename, self.db_path)
        except Exception:
            logger.exception(f"Asset lookup failed for {event.filename}")
            asset = None
        return build_track(event, asset, self.station_name)

    def record_sync(self, track: dict) -> None:
        try:
            with self._connect() as conn:
                if insert_play(conn, track):
                    logger.info(f"Recorded play {track['asset_id'][:16]} ({track['kind']}) at {track['on_air_at']}")
        except Exception:
            logger.exception(f"Failed to record play for {track.get('filename')}")

    # -- state ------------------------------------------------------------
    async def startup(self) -> None:
        try:
            recent = await asyncio.to_thread(self.load_history_sync)
            self.state.load(recent)
            cur = self.state.current
            logger.info(f"Loaded {len(recent)} plays from sqlite; current={cur['title'] if cur else None}")
        except Exception:
            logger.exception("Could not load history from sqlite")
        await self.refresh_queues(broadcast=False)
        await self.refresh_stream(broadcast=False)

    async def handle_event(self, data: dict) -> str:
        event = TrackEvent.from_json(data)
        track = await asyncio.to_thread(self.resolve_sync, event)
        async with self.lock:
            result = self.state.apply_track(track)
        lag = (datetime.now(timezone.utc) - event.on_air_at).total_seconds()
        logger.info(
            f"EVENT rid={event.rid} kind={track['kind']} title={track['title']!r} "
            f"on_air_at={track['on_air_at']} lag={lag:.3f}s -> {result}"
        )
        if result == "duplicate":
            return result
        await self.broadcast(force=result == "current")
        asyncio.create_task(asyncio.to_thread(self.record_sync, track))
        # The queue just popped; show the new next-up as soon as the socket says so.
        asyncio.create_task(self.refresh_queues())
        return result

    async def sync_from_db(self) -> None:
        """Legacy /notify path: adopt the newest play_history row if it is newer than ours."""
        try:
            recent = await asyncio.to_thread(self.load_history_sync)
        except Exception:
            logger.exception("sync_from_db failed")
            return
        if recent:
            async with self.lock:
                self.state.apply_track(recent[0])

    async def refresh_queues(self, broadcast: bool = True) -> None:
        if self.queue_fetcher is None:
            return
        try:
            queues = await asyncio.to_thread(self.queue_fetcher)
        except Exception as e:
            logger.warning(f"Queue refresh failed: {e}")
            return
        async with self.lock:
            changed = self.state.set_queues(queues.get("breaks_queue", []), queues.get("music_queue", []))
        if changed and broadcast:
            await self.broadcast()

    async def refresh_stream(self, broadcast: bool = True) -> None:
        if self.stream_fetcher is None:
            return
        try:
            stream = await asyncio.to_thread(self.stream_fetcher)
        except Exception as e:
            logger.warning(f"Icecast refresh failed: {e}")
            return
        if stream is None:
            return
        async with self.lock:
            changed = self.state.set_stream(stream)
        if changed and broadcast:
            await self.broadcast()

    async def _poll(self, interval: float, fn) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await fn()
            except Exception:
                logger.exception("poll failed")

    def start_polling(self) -> None:
        self._tasks.append(asyncio.create_task(self._poll(QUEUE_POLL_SEC, self.refresh_queues)))
        self._tasks.append(asyncio.create_task(self._poll(STREAM_POLL_SEC, self.refresh_stream)))

    # -- SSE --------------------------------------------------------------
    def payload(self) -> dict:
        return self.state.payload()

    @staticmethod
    def encode(payload: dict) -> bytes:
        return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()

    async def broadcast(self, force: bool = False) -> None:
        payload = self.payload()
        key = json.dumps({k: v for k, v in payload.items() if k not in ("updated_at", "server_time")}, sort_keys=True)
        if not force and key == self._last_broadcast_key:
            return
        self._last_broadcast_key = key
        if not self.clients:
            return
        cur = payload.get("current") or {}
        logger.info(f"Broadcasting to {len(self.clients)} clients: current={cur.get('title')!r} on_air_at={cur.get('on_air_at')}")
        message = self.encode(payload)
        for client in list(self.clients):
            try:
                await client.write(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                self.clients.discard(client)


def origin_allowed(origin: str) -> bool:
    if not origin.startswith(("http://", "https://")):
        return False
    domain = origin.split("://", 1)[1]
    return domain == "clintecker.com" or domain.endswith(".clintecker.com")


def make_app(daemon: Daemon, run_background: bool = True) -> web.Application:
    async def sse_handler(request: web.Request) -> web.StreamResponse:
        origin = request.headers.get("Origin", "")
        allowed = bool(origin) and origin_allowed(origin)
        if origin and not allowed:
            logger.warning(f"Rejected SSE connection from unauthorized origin: {origin}")
            return web.Response(text="Forbidden", status=403)

        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"
        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        await response.prepare(request)

        daemon.clients.add(response)
        logger.info(f"Client connected. Total clients: {len(daemon.clients)}")
        try:
            # server_time is stamped now, so even the first message is a valid clock sample.
            await response.write(daemon.encode(daemon.payload()))
            while True:
                await asyncio.sleep(KEEPALIVE_SEC)
                # Named event (not a comment) so the frontend's EventSource sees the keepalive.
                await response.write("event: ping\ndata: {}\n\n".encode())
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            daemon.clients.discard(response)
            logger.info(f"Client disconnected. Total clients: {len(daemon.clients)}")
        return response

    async def event_handler(request: web.Request) -> web.Response:
        try:
            data = json.loads(await request.text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return web.Response(text="Invalid JSON", status=400)
        if isinstance(data, dict) and data.get("event", "track") != "track":
            logger.info(f"Ignoring event type {data.get('event')!r}")
            return web.Response(status=204)
        try:
            result = await daemon.handle_event(data)
        except ValueError as e:
            logger.warning(f"Rejected event {data!r}: {e}")
            return web.Response(text=str(e), status=400)
        return web.json_response({"result": result})

    async def notify_handler(request: web.Request) -> web.Response:
        await daemon.sync_from_db()
        await daemon.refresh_queues(broadcast=False)
        await daemon.broadcast(force=True)
        return web.Response(text="OK")

    async def state_handler(request: web.Request) -> web.Response:
        return web.json_response(daemon.payload())

    async def on_startup(app: web.Application) -> None:
        await daemon.startup()
        if run_background:
            daemon.start_polling()

    async def on_shutdown(app: web.Application) -> None:
        for t in daemon._tasks:
            t.cancel()
        if not daemon.clients:
            return
        logger.info(f"Notifying {len(daemon.clients)} clients of restart...")
        msg = daemon.encode({"system_status": "restarting", "message": "Push service restarting - reconnecting shortly..."})
        for client in list(daemon.clients):
            try:
                await asyncio.wait_for(client.write(msg), timeout=0.5)
            except Exception:
                pass
        daemon.clients.clear()

    app = web.Application()
    app.router.add_get("/stream", sse_handler)
    app.router.add_post("/event", event_handler)
    app.router.add_post("/notify", notify_handler)
    app.router.add_get("/state", state_handler)
    async def health_handler(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app.router.add_get("/health", health_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


def main() -> None:
    from export_now_playing import get_both_queues, get_icecast_status

    daemon = Daemon(
        db_path=config.paths.db_path,
        station_name=_station_name(),
        queue_fetcher=lambda: get_both_queues(breaks_limit=3, music_limit=5),
        stream_fetcher=get_icecast_status,
    )
    app = make_app(daemon)

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    try:
        logger.info("Starting SSE push daemon on port 8001")
        web.run_app(app, host="127.0.0.1", port=8001, access_log=None)
    except KeyboardInterrupt:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
