import { describe, expect, it } from 'vitest';
import { DelayEstimator, MAX_DELAY_MS, burstSeconds, rawDelayMs } from './listener-delay';

describe('burstSeconds', () => {
  it('converts the Icecast burst to seconds of audio at the stream bitrate', () => {
    expect(burstSeconds(128)).toBeCloseTo(4.096, 3);
    expect(burstSeconds(192)).toBeCloseTo(2.731, 3);
    expect(burstSeconds(0)).toBe(0);
  });
});

describe('rawDelayMs', () => {
  const t0 = 1_000_000;
  it('equals the burst when playback kept pace with wall time', () => {
    // Connected at t0, 20 s later 20 s of audio has played: only the burst remains.
    expect(rawDelayMs({ connectedAtMs: t0, currentTime: 20, bitrateKbps: 128 }, t0 + 20_000)).toBeCloseTo(4096, 0);
  });
  it('grows by startup buffering and stalls (wall time that produced no audio)', () => {
    // 1.5 s to start + a 2 s stall: 20 s wall, 16.5 s played.
    expect(rawDelayMs({ connectedAtMs: t0, currentTime: 16.5, bitrateKbps: 128 }, t0 + 20_000)).toBeCloseTo(7596, 0);
  });
  it('clamps to 0..30 s', () => {
    expect(rawDelayMs({ connectedAtMs: t0, currentTime: 100, bitrateKbps: 128 }, t0 + 1_000)).toBe(0);
    expect(rawDelayMs({ connectedAtMs: t0, currentTime: 0, bitrateKbps: 128 }, t0 + 120_000)).toBe(MAX_DELAY_MS);
  });
});

describe('DelayEstimator', () => {
  it('takes the first sample as-is and smooths small jitter', () => {
    const e = new DelayEstimator();
    expect(e.sample(8000)).toBe(8000);
    const next = e.sample(8400);
    expect(next).toBeGreaterThan(8000);
    expect(next).toBeLessThan(8400);
  });
  it('snaps to large jumps such as a stall instead of easing in', () => {
    const e = new DelayEstimator();
    e.sample(6000);
    expect(e.sample(11_000)).toBe(11_000);
  });
  it('converges on a steady value and resets when stopped', () => {
    const e = new DelayEstimator();
    e.sample(5000);
    for (let i = 0; i < 40; i++) e.sample(6000);
    expect(e.get()).toBeCloseTo(6000, 0);
    e.reset();
    expect(e.get()).toBeNull();
  });
  it('clamps samples to the 0..30 s range', () => {
    const e = new DelayEstimator();
    expect(e.sample(-50)).toBe(0);
    e.reset();
    expect(e.sample(99_000)).toBe(MAX_DELAY_MS);
  });
});
