/** Shape of the JSON pushed by push_daemon.py on /api/stream. Mirrors export_now_playing.py. */

export type TrackKind = 'music' | 'break' | 'bumper' | 'unknown';

export interface Track {
  asset_id: string;
  title: string | null;
  artist: string | null;
  album: string | null;
  duration_sec: number | null;
  /** Origin queue: music, break (news), bumper (station ID). */
  source: string;
  kind?: string;
  /** ISO timestamp; present on current + history, absent on queued tracks. */
  played_at?: string;
}

export interface IcecastSource {
  listenurl: string;
  listeners: number;
  listener_peak: number;
  bitrate: number;
  samplerate: number;
  channels: number;
  stream_start_iso8601?: string;
  stream_start?: string;
}

export interface NowPlayingPayload {
  updated_at: string;
  /** 'online' | 'restarting' in practice; kept open for forward compatibility. */
  system_status: string;
  message?: string;
  crossfade: { music_sec: number; breaks_sec: number };
  stream: { source?: IcecastSource[] } | Record<string, never>;
  current: Track | null;
  breaks_queue: Track[];
  music_queue: Track[];
  history: Track[];
}

export type ConnectionState = 'connecting' | 'live' | 'reconnecting' | 'stale' | 'restarting';

export function trackKind(t: Track): TrackKind {
  const k = t.kind ?? t.source;
  return k === 'music' || k === 'break' || k === 'bumper' ? k : 'unknown';
}
