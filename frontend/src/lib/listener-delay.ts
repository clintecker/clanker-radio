/**
 * Listener playback delay: how far behind the encoder this listener's ears are.
 *
 * Liquidsoap stamps `on_air_at` when a track enters the encoders. A listener hears
 * that moment later by (a) the Icecast burst-on-connect, which starts every new
 * connection `burst-size` bytes in the past, plus (b) whatever the browser has
 * buffered or stalled since. Both are captured by one identity:
 *
 *   heard_now = connect_time - burst_sec + audio.currentTime
 *   delay     = now - heard_now = (now - connect_time) - audio.currentTime + burst_sec
 *
 * `now` and `connect_time` are both read from this browser's clock, so no server
 * clock sync is needed for the delay itself. Every stall freezes currentTime while
 * wall time moves on, so the delay grows exactly as the listener falls behind.
 *
 * Samples are clamped to 0-30 s and smoothed with an EMA; a jump larger than
 * SNAP_MS (a stall, a reconnect) is taken immediately instead of eased in.
 */

/** Icecast <burst-size> on the server (icecast.xml). */
export const ICECAST_BURST_BYTES = 65_535;
export const MAX_DELAY_MS = 30_000;
const SNAP_MS = 1_500;
const ALPHA = 0.25;

export function burstSeconds(bitrateKbps: number, burstBytes = ICECAST_BURST_BYTES): number {
  return bitrateKbps > 0 ? (burstBytes * 8) / (bitrateKbps * 1000) : 0;
}

export interface PlaybackTiming {
  /** Date.now() when the stream request was issued. */
  connectedAtMs: number;
  /** audio.currentTime in seconds: how much audio has actually been played. */
  currentTime: number;
  bitrateKbps: number;
}

/** Unsmoothed, clamped delay in ms for one observation at wall time `nowMs`. */
export function rawDelayMs(t: PlaybackTiming, nowMs: number): number {
  const d = nowMs - t.connectedAtMs - t.currentTime * 1000 + burstSeconds(t.bitrateKbps) * 1000;
  return Math.min(MAX_DELAY_MS, Math.max(0, d));
}

export class DelayEstimator {
  private value: number | null = null;

  /** Feed one raw sample (ms); returns the smoothed delay. */
  sample(rawMs: number): number {
    const raw = Math.min(MAX_DELAY_MS, Math.max(0, rawMs));
    if (this.value === null || Math.abs(raw - this.value) > SNAP_MS) this.value = raw;
    else this.value += ALPHA * (raw - this.value);
    return this.value;
  }

  get(): number | null {
    return this.value;
  }

  reset(): void {
    this.value = null;
  }
}
