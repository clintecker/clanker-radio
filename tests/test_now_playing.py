"""Tests for ai_radio.now_playing: event parsing, ordering, idempotency, history, payload, sqlite."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from ai_radio.now_playing import (
    AssetInfo,
    NowPlayingState,
    TrackEvent,
    build_track,
    insert_play,
    kind_from_path,
    load_recent,
    resolve_asset,
)

T0 = datetime(2026, 9, 23, 2, 0, 0, tzinfo=timezone.utc)
STATION = "Last Byte Radio"


def ev(rid, name, at, folder="music", **extra):
    data = {"rid": str(rid), "filename": f"/srv/ai_radio/assets/{folder}/{name}.mp3", "on_air_at": at, **extra}
    return TrackEvent.from_json(data)


def track(rid, name, offset_sec, folder="music", asset=True):
    e = ev(rid, name, (T0 + timedelta(seconds=offset_sec)).timestamp(), folder)
    info = AssetInfo(f"id-{name}", f"Title {name}", "Artist", "Album", 180.0, e.kind) if asset else None
    return build_track(e, info, STATION)


# -- parsing -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path,kind",
    [
        ("/srv/ai_radio/assets/music/a.mp3", "music"),
        ("/srv/ai_radio/assets/breaks/b.mp3", "break"),
        ("/srv/ai_radio/assets/bumpers/c.mp3", "bumper"),
        ("/srv/ai_radio/assets/beds/d.mp3", "bed"),
        ("/srv/ai_radio/assets/safety/e.mp3", "safety"),
        ("/srv/ai_radio/assets/startup.mp3", "jingle"),
        ("/elsewhere/x.mp3", "unknown"),
    ],
)
def test_kind_from_path(path, kind):
    assert kind_from_path(path) == kind


def test_event_from_liquidsoap_json_uses_unix_on_air_time():
    e = TrackEvent.from_json(
        {"event": "track", "rid": 164, "filename": "/a/music/x.mp3", "kind": "music", "on_air_at": T0.timestamp(), "duration": -1.0}
    )
    assert e.rid == "164"
    assert e.on_air_at == T0
    assert e.duration_sec is None
    assert e.kind == "music"


def test_event_accepts_iso_and_infers_kind():
    e = TrackEvent.from_json({"filename": "/a/breaks/x.mp3", "on_air_at": "2026-09-23T02:00:00Z", "duration": "42.5"})
    assert e.on_air_at == T0
    assert e.kind == "break"
    assert e.duration_sec == 42.5


def test_event_without_filename_is_rejected():
    with pytest.raises(ValueError):
        TrackEvent.from_json({"rid": "1", "filename": ""})


def test_build_track_played_at_equals_on_air_at_and_falls_back_without_asset():
    t = build_track(ev(9, "brk", T0.timestamp(), "breaks"), None, STATION)
    assert t["played_at"] == t["on_air_at"] == "2026-09-23T02:00:00.000000+00:00"
    assert t["title"] == "News Break"
    assert t["artist"] == STATION
    assert t["source"] == t["kind"] == "break"


# -- state -------------------------------------------------------------------


def test_track_change_moves_current_to_history():
    s = NowPlayingState()
    a, b = track(1, "a", 0), track(2, "b", 200)
    assert s.apply_track(a) == "current"
    assert s.apply_track(b) == "current"
    assert s.current is b
    assert [h["rid"] for h in s.history] == ["1"]


def test_duplicate_event_is_ignored():
    s = NowPlayingState()
    s.apply_track(track(1, "a", 0))
    s.apply_track(track(2, "b", 200))
    assert s.apply_track(track(2, "b", 200.4)) == "duplicate"
    assert s.apply_track(track(1, "a", 0)) == "duplicate"
    assert s.current["rid"] == "2"
    assert len(s.history) == 1


def test_late_event_is_filed_in_history_in_on_air_order():
    s = NowPlayingState()
    s.apply_track(track(1, "a", 0))
    s.apply_track(track(3, "c", 400))
    assert s.apply_track(track(2, "b", 200)) == "history"
    assert s.current["rid"] == "3"
    assert [h["rid"] for h in s.history] == ["2", "1"]


def test_history_is_capped_at_15():
    s = NowPlayingState()
    for i in range(20):
        s.apply_track(track(i, f"t{i}", i * 200))
    assert len(s.history) == 15
    assert s.history[0]["rid"] == "18"


def test_beds_show_as_current_but_do_not_enter_history():
    s = NowPlayingState()
    s.apply_track(track(1, "a", 0))
    s.apply_track(track(2, "bed", 200, folder="beds", asset=False))
    assert s.current["kind"] == "bed"
    s.apply_track(track(3, "b", 300))
    assert [h["rid"] for h in s.history] == ["1"]


def test_rows_loaded_from_sqlite_dedupe_against_events_without_rid():
    s = NowPlayingState()
    row = track(1, "a", 0)
    row["rid"] = ""
    s.load([row])
    assert s.apply_track(track(77, "a", 0.2)) == "duplicate"


def test_payload_shape_matches_frontend_contract():
    s = NowPlayingState()
    s.apply_track(track(1, "a", 0))
    s.apply_track(track(2, "b", 200))
    s.set_queues([{"asset_id": "x", "title": "Station ID", "source": "bumper"}], [{"asset_id": "y", "title": "Next"}])
    s.set_stream({"source": [{"listenurl": "/radio", "bitrate": 192}]})
    now = T0 + timedelta(seconds=210)
    p = s.payload(now)
    assert set(p) == {
        "updated_at", "server_time", "system_status", "crossfade", "stream",
        "current", "breaks_queue", "music_queue", "history",
    }
    assert p["server_time"] == p["updated_at"] == now.isoformat(timespec="microseconds")
    assert p["system_status"] == "online"
    assert p["crossfade"] == {"music_sec": 4.0, "breaks_sec": 0.0}
    cur = p["current"]
    for key in ("asset_id", "title", "artist", "album", "duration_sec", "source", "kind", "played_at", "on_air_at"):
        assert key in cur
    assert cur["played_at"] == cur["on_air_at"]
    assert "filename" not in cur and all("filename" not in h for h in p["history"])
    assert p["breaks_queue"][0]["source"] == "bumper"
    assert p["stream"]["source"][0]["bitrate"] == 192


def test_set_queues_and_stream_report_changes():
    s = NowPlayingState()
    assert s.set_queues([], [{"title": "a"}]) is True
    assert s.set_queues([], [{"title": "a"}]) is False
    assert s.set_stream({"source": []}) is True
    assert s.set_stream({"source": []}) is False


# -- sqlite ------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "radio.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE assets (id TEXT PRIMARY KEY, path TEXT, kind TEXT, title TEXT, artist TEXT, album TEXT, duration_sec REAL);
        CREATE TABLE play_history (id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT NOT NULL, played_at TEXT NOT NULL,
            source TEXT NOT NULL, hour_bucket TEXT NOT NULL, duration_sec REAL);
        """
    )
    conn.execute(
        "INSERT INTO assets VALUES ('id-a', '/srv/ai_radio/assets/music/a.mp3', 'music', 'Song A', 'Clint', 'LP', 200.0)"
    )
    conn.commit()
    yield path, conn
    conn.close()


def test_insert_play_records_on_air_time_once(db):
    path, conn = db
    t = track(1, "a", 0)
    assert insert_play(conn, t) is True
    assert insert_play(conn, t) is False
    rows = conn.execute("SELECT asset_id, source, played_at, hour_bucket FROM play_history").fetchall()
    assert rows == [("id-a", "music", t["on_air_at"], "2026-09-23T02:00:00.000000+00:00")]


def test_insert_play_skips_beds_and_unknown_assets(db):
    _, conn = db
    assert insert_play(conn, track(1, "bed", 0, folder="beds", asset=False)) is False
    assert conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0] == 0


def test_resolve_asset_by_path_and_by_content_hash(db, tmp_path):
    path, conn = db
    assert resolve_asset(conn, "/srv/ai_radio/assets/music/a.mp3", path).title == "Song A"

    # A copy of known audio under an unregistered path resolves by sha256.
    import hashlib

    f = tmp_path / "music" / "copy.mp3"
    f.parent.mkdir()
    f.write_bytes(b"audio-bytes")
    digest = hashlib.sha256(b"audio-bytes").hexdigest()
    conn.execute("INSERT INTO assets VALUES (?, '/other/place.mp3', 'music', 'Copied', 'Clint', NULL, 99.0)", (digest,))
    conn.commit()
    info = resolve_asset(conn, str(f), path, ingest=lambda **kw: pytest.fail("should not ingest"))
    assert info.asset_id == digest and info.title == "Copied"


def test_resolve_asset_registers_unknown_audio(db, tmp_path):
    path, conn = db
    f = tmp_path / "bumpers" / "new.mp3"
    f.parent.mkdir()
    f.write_bytes(b"brand-new")
    import hashlib

    digest = hashlib.sha256(b"brand-new").hexdigest()

    def fake_ingest(source_path, kind, db_path, ingest_existing):
        c = sqlite3.connect(db_path)
        c.execute("INSERT INTO assets VALUES (?, ?, ?, 'New ID', NULL, NULL, 5.0)", (digest, str(source_path), kind))
        c.commit()
        c.close()

    info = resolve_asset(conn, str(f), path, ingest=fake_ingest)
    assert info.asset_id == digest and info.kind == "bumper"


def test_resolve_asset_does_not_hash_beds(db):
    path, conn = db
    assert resolve_asset(conn, "/srv/ai_radio/assets/beds/x.mp3", path) is None


def test_load_recent_seeds_state_newest_first(db):
    path, conn = db
    for i in range(3):
        insert_play(conn, track(i, "a", i * 300))
    recent = load_recent(conn, STATION)
    s = NowPlayingState()
    s.load(recent)
    assert s.current["on_air_at"] == track(2, "a", 600)["on_air_at"]
    assert s.current["title"] == "Song A"
    assert len(s.history) == 2
    assert s.history[0]["played_at"] > s.history[1]["played_at"]
