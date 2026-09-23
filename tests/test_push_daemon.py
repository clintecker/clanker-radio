"""HTTP-level tests for scripts/push_daemon.py: /event, /notify, /state and SSE broadcast."""

import asyncio
import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytest.importorskip("aiohttp")
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("push_daemon", ROOT / "scripts" / "push_daemon.py")
push_daemon = importlib.util.module_from_spec(spec)
sys.modules["push_daemon"] = push_daemon
spec.loader.exec_module(push_daemon)

T0 = datetime(2026, 9, 23, 2, 0, 0, tzinfo=timezone.utc).timestamp()


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "radio.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE assets (id TEXT PRIMARY KEY, path TEXT, kind TEXT, title TEXT, artist TEXT, album TEXT, duration_sec REAL);
        CREATE TABLE play_history (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT NOT NULL, played_at TEXT NOT NULL,
            source TEXT NOT NULL, hour_bucket TEXT NOT NULL, duration_sec REAL);
        """
    )
    for name, kind in (("a", "music"), ("b", "music"), ("c", "bumper")):
        folder = {"music": "music", "bumper": "bumpers"}[kind]
        conn.execute(
            "INSERT INTO assets VALUES (?, ?, ?, ?, 'Clint', NULL, 180.0)",
            (f"id-{name}", f"/srv/ai_radio/assets/{folder}/{name}.mp3", kind, f"Song {name.upper()}"),
        )
    conn.commit()
    conn.close()
    return path


def event(rid, name, at, folder="music"):
    return {"event": "track", "rid": str(rid), "filename": f"/srv/ai_radio/assets/{folder}/{name}.mp3", "on_air_at": at, "duration": -1.0}


def run(coro):
    return asyncio.run(coro)


async def _client(daemon):
    client = TestClient(TestServer(push_daemon.make_app(daemon, run_background=False)))
    await client.start_server()
    return client


def make_daemon(db_path, queues=None):
    return push_daemon.Daemon(
        db_path=db_path,
        station_name="Last Byte Radio",
        queue_fetcher=lambda: queues or {"breaks_queue": [], "music_queue": [{"asset_id": "id-b", "title": "Song B", "source": "music"}]},
        stream_fetcher=lambda: {"source": [{"listenurl": "/radio", "bitrate": 192}]},
    )


def test_event_updates_state_records_play_and_is_idempotent(db_path):
    async def go():
        daemon = make_daemon(db_path)
        client = await _client(daemon)
        try:
            r = await client.post("/event", data=json.dumps(event(1, "a", T0)))
            assert (await r.json())["result"] == "current"
            r = await client.post("/event", data=json.dumps(event(1, "a", T0 + 0.3)))
            assert (await r.json())["result"] == "duplicate"
            r = await client.post("/event", data=json.dumps(event(2, "c", T0 + 180, "bumpers")))
            assert (await r.json())["result"] == "current"
            await asyncio.sleep(0.2)  # background sqlite write + queue refresh
            state = await (await client.get("/state")).json()
        finally:
            await client.close()
        return state

    state = run(go())
    assert state["current"]["title"] == "Song C"
    assert state["current"]["kind"] == "bumper"
    assert state["current"]["on_air_at"].startswith("2026-09-23T02:03:00")
    assert state["current"]["played_at"] == state["current"]["on_air_at"]
    assert [h["title"] for h in state["history"]] == ["Song A"]
    assert state["music_queue"][0]["title"] == "Song B"
    assert state["stream"]["source"][0]["bitrate"] == 192
    assert "server_time" in state
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT asset_id, source FROM play_history ORDER BY played_at").fetchall()
    conn.close()
    assert rows == [("id-a", "music"), ("id-c", "bumper")]


def test_out_of_order_events_keep_newest_current(db_path):
    async def go():
        daemon = make_daemon(db_path)
        client = await _client(daemon)
        try:
            await client.post("/event", data=json.dumps(event(2, "b", T0 + 200)))
            r = await client.post("/event", data=json.dumps(event(1, "a", T0)))
            assert (await r.json())["result"] == "history"
            return await (await client.get("/state")).json()
        finally:
            await client.close()

    state = run(go())
    assert state["current"]["title"] == "Song B"
    assert [h["title"] for h in state["history"]] == ["Song A"]


def test_bad_events_are_rejected(db_path):
    async def go():
        client = await _client(make_daemon(db_path))
        try:
            assert (await client.post("/event", data="not json")).status == 400
            assert (await client.post("/event", data=json.dumps({"rid": "1"}))).status == 400
            assert (await client.post("/event", data=json.dumps({"event": "queue"}))).status == 204
        finally:
            await client.close()

    run(go())


def test_restart_loads_history_from_sqlite(db_path):
    async def go():
        d1 = make_daemon(db_path)
        c1 = await _client(d1)
        await c1.post("/event", data=json.dumps(event(1, "a", T0)))
        await c1.post("/event", data=json.dumps(event(2, "b", T0 + 200)))
        await asyncio.sleep(0.2)
        await c1.close()
        c2 = await _client(make_daemon(db_path))
        try:
            state = await (await c2.get("/state")).json()
            # Liquidsoap re-sending the current track after the restart must not duplicate it.
            r = await c2.post("/event", data=json.dumps(event(2, "b", T0 + 200)))
            assert (await r.json())["result"] == "duplicate"
        finally:
            await c2.close()
        return state

    state = run(go())
    assert state["current"]["title"] == "Song B"
    assert [h["title"] for h in state["history"]] == ["Song A"]


def test_sse_client_gets_state_then_track_change(db_path):
    async def go():
        daemon = make_daemon(db_path)
        client = await _client(daemon)
        try:
            await client.post("/event", data=json.dumps(event(1, "a", T0)))
            resp = await client.get("/stream")
            first = await resp.content.readuntil(b"\n\n")
            await client.post("/event", data=json.dumps(event(2, "b", T0 + 200)))
            second = await resp.content.readuntil(b"\n\n")
            resp.close()
            # /notify still works and rebroadcasts the daemon's own state.
            assert (await client.post("/notify", data="{}")).status == 200
        finally:
            await client.close()
        return [json.loads(m.decode()[len("data: "):]) for m in (first, second)]

    first, second = run(go())
    assert first["current"]["title"] == "Song A"
    assert second["current"]["title"] == "Song B"
    assert second["history"][0]["title"] == "Song A"
    assert second["current"]["on_air_at"] == second["current"]["played_at"]


def test_notify_adopts_newer_legacy_play_from_sqlite(db_path):
    async def go():
        daemon = make_daemon(db_path)
        client = await _client(daemon)
        try:
            await client.post("/event", data=json.dumps(event(1, "a", T0)))
            await asyncio.sleep(0.2)
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO play_history (asset_id, source, played_at, hour_bucket) VALUES ('id-b', 'music', ?, 'x')",
                ("2026-09-23T02:05:00.000000+00:00",),
            )
            conn.commit()
            conn.close()
            await client.post("/notify")
            return await (await client.get("/state")).json()
        finally:
            await client.close()

    state = run(go())
    assert state["current"]["title"] == "Song B"
    assert state["history"][0]["title"] == "Song A"


def test_origin_allowed():
    assert push_daemon.origin_allowed("https://radio.clintecker.com")
    assert push_daemon.origin_allowed("https://clintecker.com")
    assert not push_daemon.origin_allowed("https://evil-clintecker.com")
    assert not push_daemon.origin_allowed("clintecker.com")
