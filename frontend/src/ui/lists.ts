import { formatClock, formatTimeAgo, formatUptime, normalizeIso } from '../lib/format';
import type { AppState } from '../lib/store';
import { trackKind, type IcecastSource, type Track } from '../lib/types';
import { byId, el, replaceChildren } from './dom';

function trackRow(t: Track, trailing: string, opts: { muted?: boolean; prefix?: string } = {}): HTMLElement {
  const kind = trackKind(t);
  return el(
    'div',
    { class: `track track-${kind}${opts.muted ? ' track-muted' : ''}` },
    el(
      'div',
      { class: 'track-info' },
      el('div', { class: 'track-title' }, opts.prefix ? `${opts.prefix} ` : '', t.title || 'Unknown'),
      el('div', { class: 'track-artist' }, t.artist || 'Unknown Artist'),
    ),
    el('div', { class: 'track-time' }, trailing),
  );
}

/** NEXT UP: a break (if queued) always plays before the next song, so show both. */
export function renderQueue(state: AppState): void {
  const container = byId('next-track');
  const data = state.data;
  if (!data) return;
  const nextBreak = data.breaks_queue[0];
  const nextMusic = data.music_queue[0];
  const rows: HTMLElement[] = [];
  if (nextBreak) {
    rows.push(trackRow(nextBreak, formatClock(nextBreak.duration_sec)));
    if (nextMusic)
      rows.push(trackRow(nextMusic, formatClock(nextMusic.duration_sec), { muted: true, prefix: '↳ then' }));
  } else if (nextMusic) {
    rows.push(trackRow(nextMusic, formatClock(nextMusic.duration_sec)));
  } else {
    rows.push(
      el(
        'div',
        { class: 'track track-empty' },
        el(
          'div',
          { class: 'track-info' },
          el('div', { class: 'track-title' }, 'Queue empty · automation will pick the next track'),
        ),
      ),
    );
  }
  replaceChildren(container, ...rows);
}

/** RECENT TRANSMISSIONS. Re-rendered on every tick so "3m ago" keeps moving between pushes. */
export function renderHistory(state: AppState, now: Date = new Date()): void {
  const list = byId('history-list');
  const history = state.data?.history ?? [];
  if (!history.length) {
    replaceChildren(
      list,
      el(
        'div',
        { class: 'track track-empty' },
        el('div', { class: 'track-info' }, el('div', { class: 'track-title' }, 'No transmissions logged yet')),
      ),
    );
    return;
  }
  replaceChildren(
    list,
    ...history.map((t) => trackRow(t, t.played_at ? formatTimeAgo(new Date(t.played_at), now) : '')),
  );
}

export function pickSource(state: AppState, bitrate: number): IcecastSource | null {
  const sources = state.data?.stream && 'source' in state.data.stream ? (state.data.stream.source ?? []) : [];
  return sources.find((s) => s.bitrate === bitrate) ?? sources[0] ?? null;
}

export function renderStats(state: AppState, bitrate: number): void {
  const src = pickSource(state, bitrate);
  byId('listeners').textContent = src ? String(src.listeners) : '—';
  byId('bitrate').textContent = src ? `${src.bitrate} kbps` : '—';
  byId('samplerate').textContent = src ? `${(src.samplerate / 1000).toFixed(1)} kHz` : '—';
  const start = src?.stream_start_iso8601 ?? src?.stream_start;
  byId('uptime').textContent = formatUptime(start ? normalizeIso(start) : undefined);
}
