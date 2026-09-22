import { formatClock } from '../lib/format';
import type { AppState, Store } from '../lib/store';
import { trackKind, type Track } from '../lib/types';
import { byId, el, replaceChildren } from './dom';

const KIND_LABEL: Record<string, string> = {
  music: 'NOW TRANSMITTING',
  break: 'NEWS BULLETIN',
  bumper: 'STATION ID',
  unknown: 'NOW TRANSMITTING',
};

/**
 * The hero card. Content only ever reflects what the server says is playing; the
 * crossfade module animates around it but never writes a guessed title into it.
 */
export class NowPlayingView {
  private readonly card = byId('now-playing');
  private readonly label = byId('np-kind');
  private readonly title = byId('current-title');
  private readonly artist = byId('current-artist');
  private readonly meta = byId('current-meta');
  private readonly elapsed = byId('current-time');
  private readonly total = byId('total-time');
  private readonly fill = byId('progress-fill');
  private readonly progress = byId('progress');
  private startMs: number | null = null;
  private durationSec = 0;
  private lastKey: string | null = null;

  constructor(private readonly store: Store) {}

  /** Returns true when the displayed track changed (used to trigger the transition). */
  render(state: AppState): boolean {
    const current = state.data?.current ?? null;
    if (!current) {
      this.title.textContent = state.connection === 'stale' ? 'SIGNAL LOST' : 'NO SIGNAL';
      this.artist.textContent = '';
      replaceChildren(this.meta);
      this.progress.hidden = true;
      this.startMs = null;
      this.lastKey = null;
      return false;
    }

    const key = `${current.asset_id}|${current.played_at ?? ''}`;
    const changed = key !== this.lastKey;
    this.lastKey = key;

    const kind = trackKind(current);
    this.card.dataset.kind = kind;
    this.label.textContent = KIND_LABEL[kind] ?? KIND_LABEL.unknown!;
    this.title.textContent = current.title || 'Unknown Track';
    this.artist.textContent = current.artist || 'Unknown Artist';
    replaceChildren(this.meta, ...metaParts(current));

    this.durationSec = current.duration_sec ?? 0;
    this.total.textContent = formatClock(this.durationSec);
    this.startMs = current.played_at ? Date.parse(current.played_at) : null;
    this.progress.hidden = !this.startMs;
    this.tick();
    return changed;
  }

  /** Seconds elapsed on the server's clock; null when unknown. */
  elapsedSec(): number | null {
    if (this.startMs === null) return null;
    return Math.max(0, (this.store.serverNow() - this.startMs) / 1000);
  }

  remainingSec(): number | null {
    const e = this.elapsedSec();
    if (e === null || this.durationSec <= 0) return null;
    return this.durationSec - e;
  }

  /** Called on an interval: advances the clock and bar without a server round-trip. */
  tick(): void {
    const e = this.elapsedSec();
    if (e === null) return;
    const shown = this.durationSec > 0 ? Math.min(e, this.durationSec) : e;
    this.elapsed.textContent = formatClock(shown);
    const pct = this.durationSec > 0 ? (shown / this.durationSec) * 100 : 0;
    this.fill.style.width = `${pct.toFixed(2)}%`;
    // Past the end and no new track yet: the server is late (crossfade, callback lag). Show it.
    this.card.classList.toggle('is-overrun', this.durationSec > 0 && e > this.durationSec + 2);
  }
}

function metaParts(t: Track): (HTMLElement | string)[] {
  const parts: (HTMLElement | string)[] = [];
  if (t.album && t.album !== 'Unknown Album') parts.push(el('span', {}, t.album));
  const kind = trackKind(t);
  if (kind !== 'music') parts.push(el('span', { class: 'np-tag' }, kind === 'break' ? 'NEWS' : 'ID'));
  return parts.flatMap((p, i) => (i ? [' · ', p] : [p]));
}
