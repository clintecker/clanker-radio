/**
 * Console view state: the lib/ signals (feed, clock, player) plus the debug overrides,
 * resolved once so every module reads the same answer.
 */
import { computed, signal } from '@preact/signals';
import { DEBUG_ENABLED, parseDebug, type DebugFlags } from '../../debug';
import { STREAM_CORS_OK } from '../../lib/config';
import type { PlayerState } from '../../lib/player';
import { trackKind, type ConnectionState, type Track, type TrackKind } from '../../lib/types';
import { app, player, playerState } from '../../state';
import { carrierOf, type Carrier } from './select';

export const debug = signal<DebugFlags>(
  DEBUG_ENABLED && typeof location !== 'undefined' ? parseDebug(location.search) : parseDebug('', false),
);

/** Debug "drop signal" overrides the feed's connection state. */
export const connOverride = signal<ConnectionState | null>(null);
if (debug.value.conn) connOverride.value = debug.value.conn === 'dead' ? 'stale' : 'reconnecting';

export const connection = computed<ConnectionState>(() => connOverride.value ?? app.value.connection);
export const carrier = computed<Carrier>(() => carrierOf(connection.value));

/** The track on air, with the debug ?kind= override applied. */
export const current = computed<Track | null>(() => {
  const c = app.value.data?.current ?? null;
  const k = debug.value.kind;
  if (!c || !k) return c;
  return {
    ...c,
    kind: k,
    source: k,
    title: k === 'break' ? 'Bulletin — top of the hour' : 'Station ID 0xDEBG',
    asset_id: `${c.asset_id}-${k}`,
  };
});
export const currentKind = computed<TrackKind>(() => (current.value ? trackKind(current.value) : 'unknown'));

/** Player state as the panel shows it (?playing=1 fakes a live monitor without audio). */
export const debugPlaying = signal(debug.value.playing);
export const tuneState = computed<PlayerState>(() =>
  debugPlaying.value ? 'playing' : (playerState.value?.state ?? 'idle'),
);
/** One-off sub-legend on the TUNE key ("Hopping to 96k"); cleared when playback settles. */
export const tuneSub = signal<string | undefined>(undefined);

let analyser: AnalyserNode | null = null;
/** Real program tap if the stream can be analysed; null means use the model. */
export const programTap = (): AnalyserNode | null => (debugPlaying.value ? null : analyser);

/** Called inside the TUNE click (a user gesture) so the AudioContext may start. */
export function armAnalyser(): void {
  if (!STREAM_CORS_OK || analyser || !player) return;
  analyser = player.getAnalyser();
}
