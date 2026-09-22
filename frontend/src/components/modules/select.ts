/** Payload → view-model selectors for the console. Pure; unit tested. */
import { formatClock, normalizeIso } from '../../lib/format';
import {
  trackKind,
  type ConnectionState,
  type IcecastSource,
  type NowPlayingPayload,
  type Track,
  type TrackKind,
} from '../../lib/types';

/** The three carrier states the hardware can show. */
export type Carrier = 'live' | 'reconnecting' | 'nosignal';

export function carrierOf(conn: ConnectionState): Carrier {
  if (conn === 'live') return 'live';
  if (conn === 'stale') return 'nosignal';
  return 'reconnecting';
}

export const CARRIER_WORD: Record<ConnectionState, string> = {
  live: 'Holding',
  connecting: 'Acquiring',
  reconnecting: 'Jammed',
  restarting: 'Restarting',
  stale: 'No carrier',
};

export const BAND_MESSAGE: Record<Carrier, string> = {
  live: 'Carrier holding · band clean',
  reconnecting: 'Corp jammer detected · hopping frequency',
  nosignal: 'No carrier · hold position, we will find you',
};

export function sources(p: NowPlayingPayload | null): IcecastSource[] {
  const s = p?.stream && 'source' in p.stream ? (p.stream.source ?? []) : [];
  return s.filter((x) => !x.listenurl.includes('fallback'));
}

export function listenerCount(p: NowPlayingPayload | null): number {
  return sources(p).reduce((n, s) => n + s.listeners, 0);
}
export function listenerPeak(p: NowPlayingPayload | null): number {
  return sources(p).reduce((n, s) => Math.max(n, s.listener_peak), 0);
}
export function feedRates(p: NowPlayingPayload | null): string {
  const r = sources(p)
    .map((s) => s.bitrate)
    .sort((a, b) => a - b);
  return r.length ? r.join(' / ') : '—';
}

export function carrierUptime(p: NowPlayingPayload | null, now: number): string {
  const start = sources(p).find((s) => s.stream_start_iso8601)?.stream_start_iso8601;
  if (!start) return '—';
  const t = Date.parse(normalizeIso(start));
  if (Number.isNaN(t)) return '—';
  const s = Math.max(0, (now - t) / 1000);
  const pad = (n: number) => String(Math.floor(n)).padStart(2, '0');
  return `${Math.floor(s / 86400)}d ${pad((s % 86400) / 3600)}h ${pad((s % 3600) / 60)}m`;
}

/** Listener count as a three-digit odometer: [dim leading zeros, digits]. */
export function odometer(n: number): [string, string] {
  const s = String(Math.max(0, Math.min(999, Math.floor(n))));
  return ['000'.slice(s.length), s];
}

export function elapsedSec(t: Track | null, serverNow: number): number | null {
  if (!t?.played_at) return null;
  const start = Date.parse(t.played_at);
  return Number.isNaN(start) ? null : Math.max(0, (serverNow - start) / 1000);
}

export function titleOf(t: Track | null): string {
  return t?.title || (t ? 'Untitled transmission' : '');
}

export function artistLine(t: Track): string {
  const artist = t.artist || '';
  return t.album && t.album !== 'Unknown Album' && artist ? `${artist} · ${t.album}` : artist;
}

export const EYEBROW: Record<TrackKind, string> = {
  music: 'On air · music',
  break: 'Bulletin interrupt · news',
  bumper: 'On air · station ident',
  unknown: 'On air',
};

export function crossfadeFor(p: NowPlayingPayload | null, kind: TrackKind): number {
  if (!p) return 0;
  return kind === 'music' ? p.crossfade.music_sec : p.crossfade.breaks_sec;
}

export interface QueueView {
  cutIns: Track[];
  music: Track[];
  total: number;
}
export function queueOf(p: NowPlayingPayload | null): QueueView {
  const cutIns = p?.breaks_queue ?? [];
  const music = p?.music_queue ?? [];
  return { cutIns, music, total: cutIns.length + music.length };
}

export const durationLabel = (t: Track): string => (t.duration_sec ? formatClock(t.duration_sec) : '—');
export { trackKind };
