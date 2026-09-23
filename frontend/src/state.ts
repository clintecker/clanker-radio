/**
 * Reactive app state. The tested, framework-free modules in lib/ (feed, clock,
 * payload, player) push into these signals; components only read them.
 */
import { computed, signal } from '@preact/signals';
import { station } from './lib/config';
import { DelayEstimator, rawDelayMs } from './lib/listener-delay';
import { Player, type PlayerSnapshot } from './lib/player';
import { FeedConnection } from './lib/sse';
import { Store, type AppState } from './lib/store';

export const store = new Store();
export const app = signal<AppState>(store.get());
store.subscribe((s) => (app.value = s));

/** Ticks 4x/s: drives the progress bar, crossfade window and relative timestamps without a server round-trip. */
export const now = signal(Date.now());
if (typeof window !== 'undefined') window.setInterval(() => (now.value = Date.now()), 250);

/** Current time on the server's clock. */
export const serverNow = computed(() => now.value + app.value.clockOffsetMs);

/**
 * Programme time this listener is hearing: server clock minus their playback delay.
 * Progress bars and elapsed times use this so they match the audio, not the encoder.
 */
export const programNow = computed(() => serverNow.value - app.value.listenerDelayMs);

export const audioEl = typeof document !== 'undefined' ? document.createElement('audio') : null;
export const player = audioEl ? new Player(audioEl) : null;
export const playerState = signal<PlayerSnapshot | null>(player?.snapshot() ?? null);
player?.subscribe((snap) => (playerState.value = snap));

/** Re-measure the listener's playback delay once a second (see lib/listener-delay.ts). */
const delay = new DelayEstimator();
export function sampleListenerDelay(nowMs = Date.now()): void {
  const timing = player?.timing() ?? null;
  let ms = 0;
  if (timing) ms = Math.round(delay.sample(rawDelayMs(timing, nowMs)));
  else delay.reset();
  if (ms !== store.get().listenerDelayMs) store.update({ listenerDelayMs: ms });
}
if (typeof window !== 'undefined' && player) window.setInterval(() => sampleListenerDelay(), 1_000);

let feed: FeedConnection | null = null;
export function startFeed(): void {
  if (feed || typeof window === 'undefined') return;
  feed = new FeedConnection(station.sseUrl, store);
  feed.start();
}
