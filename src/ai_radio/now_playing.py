"""Now-playing state owned by the push daemon.

Liquidsoap is the single source of truth: it POSTs one event per track start,
taken from the final on-air source (after cross() and the safety fallback), with
the on-air time stamped inside Liquidsoap. This module turns those events into
the JSON payload the frontend consumes. It is pure (no I/O) so it can be tested
directly; scripts/push_daemon.py does the networking, sqlite and socket work.

Payload shape is the one export_now_playing.py produced (frontend/src/lib/types.ts),
plus ``current.on_air_at`` (authoritative ISO on-air time; ``played_at`` equals it)
and top-level ``server_time``.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

HISTORY_SIZE = 15
# Kinds that are real programme items: recorded to play_history and kept in history.
RECORDED_KINDS = ("music", "break", "bumper")
CROSSFADE = {"music_sec": 4.0, "breaks_sec": 0.0}
# Two events for the same request within this window are the same play.
DUPLICATE_WINDOW_SEC = 60.0


def kind_from_path(path: str) -> str:
    """Classify an on-air file by the folder it lives in."""
    for folder, kind in (
        ("/bumpers/", "bumper"),
        ("/breaks/", "break"),
        ("/music/", "music"),
        ("/beds/", "bed"),
        ("/safety/", "safety"),
    ):
        if folder in path:
            return kind
    if path.endswith("/startup.mp3"):
        return "jingle"
    return "unknown"


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def parse_time(value: Any) -> Optional[datetime]:
    """Accept unix seconds (Liquidsoap's time()) or an ISO string."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value <= 0:
            return None
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return parse_time(float(value))
            except ValueError:
                return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


@dataclass(frozen=True)
class TrackEvent:
    """One track start as reported by Liquidsoap."""

    rid: str
    filename: str
    kind: str
    on_air_at: datetime
    duration_sec: Optional[float] = None
    title: Optional[str] = None
    artist: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict, now: Optional[datetime] = None) -> "TrackEvent":
        if not isinstance(data, dict):
            raise ValueError("event must be an object")
        filename = str(data.get("filename") or "")
        if not filename:
            raise ValueError("event has no filename")
        on_air = parse_time(data.get("on_air_at")) or now or datetime.now(timezone.utc)
        duration = data.get("duration")
        try:
            duration = float(duration) if duration not in (None, "") else None
        except (TypeError, ValueError):
            duration = None
        if duration is not None and duration <= 0:
            duration = None
        kind = str(data.get("kind") or "") or kind_from_path(filename)
        return cls(
            rid=str(data.get("rid") or ""),
            filename=filename,
            kind=kind,
            on_air_at=on_air,
            duration_sec=duration,
            title=(str(data["title"]) if data.get("title") else None),
            artist=(str(data["artist"]) if data.get("artist") else None),
        )


@dataclass(frozen=True)
class AssetInfo:
    asset_id: Optional[str]
    title: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    duration_sec: Optional[float]
    kind: Optional[str]


def default_title(kind: str, filename: str) -> str:
    return {
        "break": "News Break",
        "bumper": "Station ID",
        "bed": "Station Bed",
        "safety": "Stand By",
        "jingle": "Station Startup",
    }.get(kind, Path(filename).stem or "Unknown")


def build_track(event: TrackEvent, asset: Optional[AssetInfo], station_name: str) -> dict:
    """Payload track dict for an event, enriched from the assets table when known."""
    kind = event.kind
    if asset and asset.kind in RECORDED_KINDS and kind not in RECORDED_KINDS:
        kind = asset.kind
    title = (asset and asset.title) or event.title or default_title(kind, event.filename)
    artist = (asset and asset.artist) or event.artist or station_name
    on_air = to_iso(event.on_air_at)
    duration = (asset and asset.duration_sec) or event.duration_sec
    return {
        "asset_id": (asset and asset.asset_id) or "",
        "title": title,
        "artist": artist,
        "album": asset.album if asset else None,
        "duration_sec": duration,
        "played_at": on_air,
        "on_air_at": on_air,
        "source": kind,
        "kind": kind,
        "rid": event.rid,
        "filename": event.filename,
    }


def _ts(track: dict) -> datetime:
    return parse_time(track.get("on_air_at") or track.get("played_at")) or datetime.min.replace(tzinfo=timezone.utc)


def _same_play(a: dict, b: dict) -> bool:
    if a.get("filename") != b.get("filename"):
        return False
    # Rows loaded from sqlite have no rid; only compare when both sides know it.
    if a.get("rid") and b.get("rid") and a.get("rid") != b.get("rid"):
        return False
    return abs((_ts(a) - _ts(b)).total_seconds()) <= DUPLICATE_WINDOW_SEC


class NowPlayingState:
    """In-memory current / history / queues / stream, ordered by on-air time."""

    def __init__(self, history_size: int = HISTORY_SIZE):
        self.history_size = history_size
        self.current: Optional[dict] = None
        self.history: list[dict] = []
        self.breaks_queue: list[dict] = []
        self.music_queue: list[dict] = []
        self.stream: dict = {}
        self.system_status = "online"

    # -- mutation -------------------------------------------------------
    def load(self, recent: list[dict]) -> None:
        """Seed from play_history rows (any order); the newest becomes current."""
        items = sorted(recent, key=_ts, reverse=True)
        for t in items:
            t.setdefault("on_air_at", t.get("played_at"))
            t.setdefault("kind", t.get("source"))
            t.setdefault("rid", "")
            t.setdefault("filename", "")
        self.current = items[0] if items else None
        self.history = items[1 : 1 + self.history_size]

    def is_duplicate(self, track: dict) -> bool:
        return any(_same_play(track, t) for t in ([self.current] if self.current else []) + self.history)

    def apply_track(self, track: dict) -> str:
        """Apply a track start. Returns 'current', 'history' (late event) or 'duplicate'."""
        if self.is_duplicate(track):
            return "duplicate"
        if self.current is None or _ts(track) >= _ts(self.current):
            if self.current is not None and self.current.get("kind") in RECORDED_KINDS:
                self.history.insert(0, self.current)
            self.current = track
        elif track.get("kind") in RECORDED_KINDS:
            # Arrived out of order: it already ended, file it where it belongs.
            self.history.append(track)
            self.history.sort(key=_ts, reverse=True)
        else:
            return "duplicate"
        del self.history[self.history_size :]
        return "current" if self.current is track else "history"

    def set_queues(self, breaks_queue: list[dict], music_queue: list[dict]) -> bool:
        changed = (breaks_queue, music_queue) != (self.breaks_queue, self.music_queue)
        self.breaks_queue, self.music_queue = breaks_queue, music_queue
        return changed

    def set_stream(self, stream: Optional[dict]) -> bool:
        stream = stream or {}
        changed = stream != self.stream
        self.stream = stream
        return changed

    # -- output ---------------------------------------------------------
    def payload(self, now: Optional[datetime] = None) -> dict:
        now_iso = to_iso(now or datetime.now(timezone.utc))
        return {
            "updated_at": now_iso,
            "server_time": now_iso,
            "system_status": self.system_status,
            "crossfade": dict(CROSSFADE),
            "stream": self.stream,
            "current": _public(self.current),
            "breaks_queue": self.breaks_queue,
            "music_queue": self.music_queue,
            "history": [_public(t) for t in self.history],
        }


def _public(track: Optional[dict]) -> Optional[dict]:
    if track is None:
        return None
    return {k: v for k, v in track.items() if k != "filename"}


# ---------------------------------------------------------------------------
# sqlite helpers (synchronous; the daemon calls them from a worker thread)
# ---------------------------------------------------------------------------


def lookup_asset(conn: sqlite3.Connection, path: str) -> Optional[AssetInfo]:
    row = conn.execute(
        "SELECT id, title, artist, album, duration_sec, kind FROM assets WHERE path = ?", (path,)
    ).fetchone()
    return AssetInfo(*row) if row else None


def resolve_unknown_asset(
    conn: sqlite3.Connection,
    file_path: str,
    db_path: Path,
    ingest: Optional[Callable[..., Any]] = None,
) -> Optional[tuple[str, str]]:
    """Find an asset by audio content when its path isn't registered, else register it in place.

    Returns (asset_id, kind) or None. Every branch logs a WARNING so unregistered files are visible.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"UNREGISTERED FILE (missing on disk): {file_path}")
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    asset_id = h.hexdigest()
    row = conn.execute("SELECT id, kind FROM assets WHERE id = ?", (asset_id,)).fetchone()
    if row:
        logger.warning(f"UNREGISTERED PATH, known audio: {file_path} is a copy of asset {asset_id[:16]}; recording that asset")
        return row
    kind = kind_from_path(file_path)
    if kind not in RECORDED_KINDS:
        kind = "music"
    logger.warning(f"UNREGISTERED FILE: registering {file_path} as new {kind} asset {asset_id[:16]}")
    try:
        if ingest is None:
            from ai_radio.ingest import ingest_audio_file as ingest
        ingest(source_path=path, kind=kind, db_path=db_path, ingest_existing=True)
    except Exception:
        logger.exception(f"Auto-registration failed for {file_path}")
        return None
    return conn.execute("SELECT id, kind FROM assets WHERE id = ?", (asset_id,)).fetchone()


def resolve_asset(conn: sqlite3.Connection, path: str, db_path: Path, ingest=None) -> Optional[AssetInfo]:
    """Asset for an on-air path: by path, else by content hash (registering if new)."""
    info = lookup_asset(conn, path)
    if info:
        return info
    if kind_from_path(path) in ("bed", "safety", "jingle"):
        return None  # beds / safety / startup are not catalogued plays
    row = resolve_unknown_asset(conn, path, db_path, ingest=ingest)
    conn.commit()
    if not row:
        return None
    r = conn.execute(
        "SELECT id, title, artist, album, duration_sec, kind FROM assets WHERE id = ?", (row[0],)
    ).fetchone()
    return AssetInfo(*r) if r else None


def insert_play(conn: sqlite3.Connection, track: dict) -> bool:
    """Record a play at its on-air time. Idempotent on (asset_id, played_at)."""
    asset_id = track.get("asset_id")
    source = track.get("kind")
    if not asset_id or source not in RECORDED_KINDS:
        return False
    played = parse_time(track["on_air_at"])
    if played is None:
        return False
    played_at = to_iso(played)
    exists = conn.execute(
        "SELECT 1 FROM play_history WHERE asset_id = ? AND played_at = ?", (asset_id, played_at)
    ).fetchone()
    if exists:
        return False
    hour_bucket = to_iso(played.replace(minute=0, second=0, microsecond=0))
    conn.execute(
        "INSERT INTO play_history (asset_id, source, played_at, hour_bucket) VALUES (?, ?, ?, ?)",
        (asset_id, source, played_at, hour_bucket),
    )
    conn.commit()
    return True


def load_recent(conn: sqlite3.Connection, station_name: str, limit: int = HISTORY_SIZE + 1) -> list[dict]:
    """Recent plays as payload tracks (newest first)."""
    rows = conn.execute(
        """
        SELECT ph.asset_id, a.title, a.artist, a.album, a.duration_sec, ph.played_at, ph.source, a.path
        FROM play_history ph LEFT JOIN assets a ON ph.asset_id = a.id
        WHERE ph.source IN ('music', 'break', 'bumper')
        ORDER BY ph.played_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out = []
    for asset_id, title, artist, album, duration, played_at, source, path in rows:
        played = parse_time(played_at)
        iso = to_iso(played) if played else played_at
        out.append(
            {
                "asset_id": asset_id,
                "title": title or default_title(source, path or ""),
                "artist": artist or station_name,
                "album": album,
                "duration_sec": duration,
                "played_at": iso,
                "on_air_at": iso,
                "source": source,
                "kind": source,
                "rid": "",
                "filename": path or "",
            }
        )
    return out
