import { describe, expect, it, vi } from 'vitest';
import { Filament, PowerSequence, STANDBY_LUM, THUMP_AT_MS, flickerLum } from './lamp';
import { Loop, MAX_DT, type LoopDeps } from './loop';
import { newKey, rekeyFrame, scrambleDuration, scrambleFrame, Scrambler } from './scramble';
import { DETENT, Spring } from './spring';
import { ProgramLevel, ProgramModel, VU_REST, VU_SPRING, rmsDbfs, vuP } from './vu';

const run = (s: Spring, seconds: number, fps = 60, reduced = false) => {
  let peak = -Infinity;
  for (let t = 0; t < seconds; t += 1 / fps) peak = Math.max(peak, s.step(1 / fps, reduced));
  return peak;
};
const seq = (seed = 7) => {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
};

describe('spring', () => {
  it('settles on its target', () => {
    const s = new Spring({ w: 15, z: 1 }, 0);
    s.target = 0.62;
    run(s, 2);
    expect(s.x).toBeCloseTo(0.62, 3);
    expect(s.settled()).toBe(true);
  });

  it('overshoot is bounded by the damping ratio', () => {
    const vu = new Spring(VU_SPRING, 0);
    vu.target = 0.8;
    expect(run(vu, 2)).toBeLessThan(0.8 * 1.05);
    const knob = new Spring(DETENT, 0);
    knob.target = 52;
    const peak = run(knob, 1.5);
    expect(peak).toBeGreaterThan(52); // a detent should visibly pass the click
    expect(peak).toBeLessThan(52 * 1.3);
    expect(knob.x).toBeCloseTo(52, 1);
  });

  it('bounces off its end stops and never leaves them', () => {
    const s = new Spring({ w: 20, z: 0.1, min: 0, max: 1, restitution: 0.28 }, 0.5);
    s.target = 3;
    let lo = Infinity,
      hi = -Infinity;
    for (let i = 0; i < 120; i++) {
      s.step(1 / 60);
      lo = Math.min(lo, s.x);
      hi = Math.max(hi, s.x);
    }
    expect(hi).toBe(1);
    expect(lo).toBeGreaterThanOrEqual(0);
  });

  it('is frame-rate independent', () => {
    const a = new Spring(VU_SPRING, 0),
      b = new Spring(VU_SPRING, 0);
    a.target = b.target = 0.7;
    run(a, 0.25, 30);
    run(b, 0.25, 120);
    expect(a.x).toBeCloseTo(b.x, 2);
  });

  it('snaps under reduced motion', () => {
    const s = new Spring(VU_SPRING, 0);
    s.target = 0.4;
    s.kick(10);
    s.step(1 / 60, true);
    expect(s.x).toBe(0.4);
    expect(s.v).toBe(0);
  });
});

describe('VU ballistics', () => {
  it('reaches ~99% of a 0 VU step in about 300 ms without pinning', () => {
    const s = new Spring(VU_SPRING, VU_REST);
    s.target = vuP(0);
    let at90 = 0;
    for (let t = 0; t < 1; t += 0.001) {
      s.step(0.001);
      if (!at90 && s.x >= 0.9 * s.target) at90 = t;
    }
    expect(at90).toBeGreaterThan(0.08);
    expect(at90).toBeLessThan(0.3);
    expect(s.x).toBeCloseTo(vuP(0), 2);
  });

  it('maps dB to the printed scale', () => {
    expect(vuP(3)).toBeCloseTo(1, 6);
    expect(vuP(0)).toBeCloseTo(0.708, 3);
    expect(vuP(-20)).toBeLessThan(0.1);
  });

  it('measures RMS of a byte buffer', () => {
    expect(rmsDbfs(new Uint8Array(64).fill(128))).toBe(-Infinity);
    const full = new Uint8Array(64).map((_, i) => (i % 2 ? 255 : 1));
    expect(rmsDbfs(full)).toBeCloseTo(0, 0);
  });

  it('models speech with gaps and music with a beat', () => {
    const m = new ProgramModel(seq());
    const speech = Array.from({ length: 400 }, (_, i) => m.db(i / 20, 'break'));
    expect(Math.min(...speech)).toBe(-26);
    const music = Array.from({ length: 400 }, (_, i) => m.db(i / 20, 'music'));
    expect(Math.max(...music)).toBeLessThan(3);
    expect(Math.min(...music)).toBeGreaterThan(-20);
  });

  it('uses the real analyser, and falls back after ~2 s of pure silence while playing', () => {
    const lvl = new ProgramLevel(seq());
    let value = 200;
    const analyser = {
      fftSize: 32,
      getByteTimeDomainData: (b: Uint8Array) => b.forEach((_, i) => (b[i] = i % 2 ? value : 256 - value)),
    };
    expect(lvl.read(0, 1 / 60, 'music', analyser).real).toBe(true);
    value = 128;
    for (let i = 0; i < 100; i++) lvl.read(i / 60, 1 / 60, 'music', analyser);
    expect(lvl.source).toBe('real');
    for (let i = 0; i < 30; i++) lvl.read(i / 60, 1 / 60, 'music', analyser);
    expect(lvl.source).toBe('simulated');
    expect(lvl.read(3, 1 / 60, 'music', analyser).real).toBe(false);
    lvl.reset();
    expect(lvl.source).toBe('real');
    expect(lvl.read(3, 1 / 60, 'music', null).real).toBe(false);
  });
});

describe('lamp', () => {
  it('warms fast and cools slow', () => {
    const f = new Filament();
    f.target = 1;
    f.step(0.05);
    const warm = f.value;
    f.target = 0;
    f.step(0.05);
    expect(warm).toBeGreaterThan(0.7);
    expect(f.value).toBeGreaterThan(0.4); // still glowing 50 ms after switch-off
    f.step(0.05, true);
    expect(f.value).toBe(0);
  });

  it('power-up flickers, thumps once, then settles at full', () => {
    expect(flickerLum(60)).toBeLessThan(0.5);
    expect(flickerLum(600)).toBe(1);
    const p = new PowerSequence();
    p.up(0);
    const thumps = [0, 100, THUMP_AT_MS + 1, 300, 500, 1000].filter((t) => p.step(t));
    expect(thumps).toEqual([THUMP_AT_MS + 1]);
    expect(p.lum).toBe(1);
    expect(p.active).toBe(false);
    p.down(1000);
    p.step(1240);
    expect(p.lum).toBeGreaterThan(STANDBY_LUM);
    p.step(1500);
    expect(p.lum).toBe(STANDBY_LUM);
  });

  it('power steps straight to its end state with reduced motion', () => {
    const p = new PowerSequence();
    p.up(0, true);
    expect(p.lum).toBe(1);
    expect(p.active).toBe(false);
    p.down(0, true);
    expect(p.lum).toBe(STANDBY_LUM);
  });
});

describe('scramble', () => {
  it('resolves left to right to the exact text, per code point', () => {
    const text = 'ЛИТАНИЯ 夜 <b>x</b>';
    const chars = Array.from(text);
    const dur = scrambleDuration(chars.length);
    const early = scrambleFrame(chars, 0, dur, seq());
    expect(Array.from(early)).toHaveLength(chars.length);
    expect(early).not.toBe(text);
    expect(early[7]).toBe(' '); // spaces never scramble
    expect(scrambleFrame(chars, dur + 60, dur, seq())).toBe(text);
  });

  it('drives at VFD refresh rate and ends on the text', () => {
    const s = new Scrambler(seq());
    s.start('GASOLINE SMILE', 1000);
    expect(s.frame(1000)).not.toBeNull();
    expect(s.frame(1010)).toBeNull(); // < 34 ms later
    let last: string | null = null;
    for (let t = 1000; t < 2000; t += 16) last = s.frame(t) ?? last;
    expect(last).toBe('GASOLINE SMILE');
    expect(s.running).toBe(false);
  });

  it('skips the effect under reduced motion', () => {
    const s = new Scrambler();
    s.start('X', 0, true);
    expect(s.running).toBe(false);
    expect(s.frame(10)).toBeNull();
  });

  it('re-keys hex groups, separators fixed', () => {
    const k = newKey(seq());
    expect(k).toMatch(/^[0-9A-F]{4}·[0-9A-F]{4}·[0-9A-F]{4}$/);
    const mid = rekeyFrame(k, 0, seq(3));
    expect(mid[4]).toBe('·');
    expect(rekeyFrame(k, 10_000)).toBe(k);
  });
});

describe('loop', () => {
  function harness(hidden = false) {
    const cbs = new Map<number, (t: number) => void>();
    let next = 1;
    const listeners: (() => void)[] = [];
    const doc = {
      hidden,
      addEventListener: (_: 'visibilitychange', fn: () => void) => void listeners.push(fn),
    };
    const deps: LoopDeps = {
      raf: (cb) => {
        cbs.set(next, cb);
        return next++;
      },
      caf: (id) => void cbs.delete(id),
      now: () => 0,
      doc,
    };
    const fire = (t: number) => {
      const pending = [...cbs.values()];
      cbs.clear();
      pending.forEach((cb) => cb(t));
    };
    const setHidden = (h: boolean) => {
      doc.hidden = h;
      listeners.forEach((l) => l());
    };
    return { loop: new Loop(deps), fire, setHidden, pending: () => cbs.size };
  }

  it('runs only while subscribed, with clamped dt', () => {
    const h = harness();
    expect(h.loop.running).toBe(false);
    const fn = vi.fn();
    const off = h.loop.add(fn);
    expect(h.loop.running).toBe(true);
    h.fire(16);
    expect(fn).toHaveBeenLastCalledWith(0.016, 16);
    h.fire(5000);
    expect(fn.mock.lastCall?.[0]).toBe(MAX_DT);
    off();
    expect(h.loop.running).toBe(false);
    expect(h.pending()).toBe(0);
  });

  it('pauses while the tab is hidden and resumes when visible', () => {
    const h = harness();
    const fn = vi.fn();
    h.loop.add(fn);
    h.setHidden(true);
    expect(h.loop.running).toBe(false);
    h.fire(16);
    expect(fn).not.toHaveBeenCalled();
    h.setHidden(false);
    expect(h.loop.running).toBe(true);
    h.fire(32);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('does not start in a hidden tab', () => {
    const h = harness(true);
    h.loop.add(() => undefined);
    expect(h.loop.running).toBe(false);
  });

  it('drops a callback that throws and keeps the others running', () => {
    const h = harness();
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const good = vi.fn();
    h.loop.add(() => {
      throw new Error('boom');
    });
    h.loop.add(good);
    h.fire(16);
    h.fire(32);
    expect(good).toHaveBeenCalledTimes(2);
    expect(h.loop.size).toBe(1);
    err.mockRestore();
  });

  it('reports reduced motion from the media query and follows changes', () => {
    let change: ((e: { matches: boolean }) => void) | undefined;
    const l = new Loop({
      raf: () => 1,
      caf: () => undefined,
      now: () => 0,
      reducedMotion: { matches: true, addEventListener: (_t, fn) => (change = fn) },
    });
    expect(l.reduced).toBe(true);
    change?.({ matches: false });
    expect(l.reduced).toBe(false);
  });
});
