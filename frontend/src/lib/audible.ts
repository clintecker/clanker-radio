import type { NowPlayingPayload } from './types';

/**
 * Applies payloads at the moment the listener can hear them.
 *
 * A payload describes the station as of its `current.on_air_at` (server clock).
 * This listener hears that moment `delayMs` later, so the payload is shown at
 * on_air_at + delay. Payloads are strictly FIFO: a later payload never overtakes
 * an earlier pending one, so two quick track changes always apply in order.
 * The due time is recomputed on every check, so tuning in or out (delay changes)
 * re-times what is still pending.
 */
export interface AudibleClock {
  /** Current time on the server's clock, ms. */
  serverNow(): number;
  /** This listener's playback delay, ms (0 when not tuned in). */
  delayMs(): number;
}

export function onAirMs(p: NowPlayingPayload): number | null {
  const iso = p.current?.on_air_at;
  if (!iso) return null;
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}

export class AudibleQueue {
  private pending: { payload: NowPlayingPayload; onAir: number | null }[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly clock: AudibleClock,
    private readonly apply: (p: NowPlayingPayload) => void,
  ) {}

  push(payload: NowPlayingPayload): void {
    this.pending.push({ payload, onAir: onAirMs(payload) });
    this.flush();
  }

  /** Number of payloads still waiting to become audible. */
  get size(): number {
    return this.pending.length;
  }

  /** Apply everything that is due, then arm a timer for the next item. */
  flush(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    const now = this.clock.serverNow();
    const delay = this.clock.delayMs();
    let latest: NowPlayingPayload | null = null;
    for (let head = this.pending[0]; head; head = this.pending[0]) {
      const due = head.onAir === null ? -Infinity : head.onAir + delay;
      if (due > now) {
        this.timer = setTimeout(() => this.flush(), Math.min(due - now, 30_000) + 5);
        break;
      }
      latest = head.payload;
      this.pending.shift();
    }
    if (latest) this.apply(latest);
  }

  clear(): void {
    this.pending = [];
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }
}
