/**
 * Reactive app state. The tested, framework-free modules in lib/ (feed, clock,
 * payload, player) push into these signals; components only read them.
 */
import { computed, signal } from '@preact/signals';
import { station } from './lib/config';
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

export const audioEl = typeof document !== 'undefined' ? document.createElement('audio') : null;
export const player = audioEl ? new Player(audioEl) : null;
export const playerState = signal<PlayerSnapshot | null>(player?.snapshot() ?? null);
player?.subscribe((snap) => (playerState.value = snap));

let feed: FeedConnection | null = null;
export function startFeed(): void {
  if (feed || typeof window === 'undefined') return;
  feed = new FeedConnection(station.sseUrl, store);
  feed.start();
}
