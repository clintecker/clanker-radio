import type { IcecastSource, NowPlayingPayload, Track } from './types';

/**
 * Runtime validation for the SSE payload.
 *
 * The daemon is ours, but the page must survive a half-deployed backend, a
 * proxy error page, or a schema change without a blank screen. Unknown or
 * malformed fields degrade to safe defaults; only a payload with no usable
 * shape at all is rejected.
 */
export class PayloadError extends Error {}

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string | null => (typeof v === 'string' ? v : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

function track(v: unknown): Track | null {
  if (!isObj(v)) return null;
  const asset_id = str(v.asset_id) ?? '';
  const title = str(v.title);
  if (!asset_id && !title) return null;
  const t: Track = {
    asset_id,
    title,
    artist: str(v.artist),
    album: str(v.album),
    duration_sec: num(v.duration_sec),
    source: str(v.source) ?? 'unknown',
  };
  const kind = str(v.kind);
  if (kind) t.kind = kind;
  const played_at = str(v.played_at);
  if (played_at) t.played_at = played_at;
  const on_air_at = str(v.on_air_at);
  if (on_air_at) t.on_air_at = on_air_at;
  return t;
}

function trackList(v: unknown): Track[] {
  return Array.isArray(v) ? v.map(track).filter((t): t is Track => t !== null) : [];
}

function source(v: unknown): IcecastSource | null {
  if (!isObj(v)) return null;
  const bitrate = num(v.bitrate);
  if (bitrate === null) return null;
  const s: IcecastSource = {
    listenurl: str(v.listenurl) ?? '',
    listeners: num(v.listeners) ?? 0,
    listener_peak: num(v.listener_peak) ?? 0,
    bitrate,
    samplerate: num(v.samplerate) ?? 0,
    channels: num(v.channels) ?? 2,
  };
  const start = str(v.stream_start_iso8601) ?? str(v.stream_start);
  if (start) s.stream_start_iso8601 = start;
  return s;
}

export function parsePayload(raw: unknown): NowPlayingPayload {
  if (!isObj(raw)) throw new PayloadError('payload is not an object');
  if (!('current' in raw) && !('system_status' in raw)) throw new PayloadError('payload has no current/system_status');

  const crossfade = isObj(raw.crossfade) ? raw.crossfade : {};
  const stream = isObj(raw.stream) ? raw.stream : {};
  const sources = Array.isArray(stream.source)
    ? stream.source.map(source).filter((s): s is IcecastSource => s !== null)
    : [];

  const payload: NowPlayingPayload = {
    updated_at: str(raw.updated_at) ?? '',
    system_status: str(raw.system_status) ?? 'online',
    crossfade: {
      music_sec: num(crossfade.music_sec) ?? 0,
      breaks_sec: num(crossfade.breaks_sec) ?? 0,
    },
    stream: sources.length ? { source: sources } : {},
    current: track(raw.current),
    breaks_queue: trackList(raw.breaks_queue),
    music_queue: trackList(raw.music_queue),
    history: trackList(raw.history),
  };
  const server_time = str(raw.server_time);
  if (server_time) payload.server_time = server_time;
  const message = str(raw.message);
  if (message) payload.message = message;
  return payload;
}
