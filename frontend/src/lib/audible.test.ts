import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AudibleQueue } from './audible';
import type { NowPlayingPayload } from './types';

const T0 = Date.parse('2026-09-23T02:00:00Z');

function payload(title: string, onAirMs: number | null): NowPlayingPayload {
  const iso = onAirMs === null ? undefined : new Date(onAirMs).toISOString();
  return {
    updated_at: '',
    system_status: 'online',
    crossfade: { music_sec: 4, breaks_sec: 0 },
    stream: {},
    current: {
      asset_id: title,
      title,
      artist: null,
      album: null,
      duration_sec: 180,
      source: 'music',
      played_at: iso,
      on_air_at: iso,
    },
    breaks_queue: [],
    music_queue: [],
    history: [],
  };
}

describe('AudibleQueue', () => {
  let delay = 0;
  let shown: string[] = [];
  let q: AudibleQueue;
  const title = () => shown[shown.length - 1];

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0);
    delay = 0;
    shown = [];
    q = new AudibleQueue({ serverNow: () => Date.now(), delayMs: () => delay }, (p) => shown.push(p.current!.title!));
  });
  afterEach(() => vi.useRealTimers());

  it('applies immediately when not tuned in (delay 0) and on_air_at has passed', () => {
    q.push(payload('A', T0));
    expect(title()).toBe('A');
  });

  it('keeps the old track for 8 s when the change is audible 8 s from now, then switches', () => {
    q.push(payload('A', T0 - 60_000));
    delay = 8000;
    q.push(payload('B', T0)); // on air now at the encoder; this listener hears it at T0 + 8 s
    expect(title()).toBe('A');
    vi.advanceTimersByTime(7_900);
    expect(title()).toBe('A');
    vi.advanceTimersByTime(200);
    expect(title()).toBe('B');
    expect(q.size).toBe(0);
  });

  it('applies two quick changes in order, each at its own audible time', () => {
    delay = 8000;
    q.push(payload('A', T0 - 60_000));
    q.push(payload('B', T0));
    q.push(payload('C', T0 + 3_000)); // arrives in the same instant, e.g. a short station ID
    expect(shown).toEqual(['A']);
    vi.advanceTimersByTime(8_100);
    expect(shown).toEqual(['A', 'B']);
    vi.advanceTimersByTime(3_000);
    expect(shown).toEqual(['A', 'B', 'C']);
  });

  it('never lets a later update overtake a pending track change', () => {
    delay = 8000;
    q.push(payload('A', T0 - 60_000));
    q.push(payload('B', T0));
    q.push(payload('stats-only', null)); // no on_air_at: would be due now, but must wait behind B
    expect(shown).toEqual(['A']);
    vi.advanceTimersByTime(8_100);
    expect(shown).toEqual(['A', 'stats-only']);
  });

  it('re-times pending changes when the listener tunes out', () => {
    delay = 10_000;
    q.push(payload('B', T0));
    expect(shown).toEqual([]);
    delay = 0;
    q.flush();
    expect(shown).toEqual(['B']);
  });
});
