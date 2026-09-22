/**
 * One requestAnimationFrame loop for every moving part (needles, lamps, knob, band watch,
 * text scrambles). Components register a callback and write through refs / CSS custom
 * properties, so Preact never re-renders at 60 Hz. The loop runs only while something is
 * subscribed and the tab is visible, and it owns the reduced-motion decision.
 */

export type FrameFn = (dt: number, now: number) => void;

interface DocLike {
  readonly hidden: boolean;
  addEventListener(type: 'visibilitychange', fn: () => void): void;
}
interface MqlLike {
  readonly matches: boolean;
  addEventListener?(type: 'change', fn: (e: { matches: boolean }) => void): void;
}

export interface LoopDeps {
  raf: (cb: (t: number) => void) => number;
  caf: (id: number) => void;
  now: () => number;
  doc?: DocLike | null;
  reducedMotion?: MqlLike | null;
}

/** Longest step we integrate; a backgrounded or janky frame must not fling a needle. */
export const MAX_DT = 0.1; // springs sub-step, so a slow frame stays real-time instead of slow-motion

export class Loop {
  private readonly subs = new Set<FrameFn>();
  private id = 0;
  private last = 0;
  private _reduced: boolean;

  constructor(private readonly deps: LoopDeps) {
    this._reduced = deps.reducedMotion?.matches ?? false;
    deps.reducedMotion?.addEventListener?.('change', (e) => (this._reduced = e.matches));
    deps.doc?.addEventListener('visibilitychange', () => this.sync());
  }

  /** True when the user asked for reduced motion: springs snap, lamps step, scrambles skip. */
  get reduced(): boolean {
    return this._reduced;
  }
  set reduced(v: boolean) {
    this._reduced = v;
  }

  get running(): boolean {
    return this.id !== 0;
  }

  get size(): number {
    return this.subs.size;
  }

  add(fn: FrameFn): () => void {
    this.subs.add(fn);
    this.sync();
    return () => {
      this.subs.delete(fn);
      this.sync();
    };
  }

  private sync(): void {
    const want = this.subs.size > 0 && !(this.deps.doc?.hidden ?? false);
    if (want && !this.id) {
      this.last = this.deps.now();
      this.id = this.deps.raf(this.tick);
    } else if (!want && this.id) {
      this.deps.caf(this.id);
      this.id = 0;
    }
  }

  private readonly tick = (t: number): void => {
    const dt = Math.min(MAX_DT, Math.max(0, (t - this.last) / 1000));
    this.last = t;
    for (const fn of [...this.subs]) {
      try {
        fn(dt, t);
      } catch (err) {
        // One broken instrument must not freeze the whole panel.
        console.error('frame callback failed', err);
        this.subs.delete(fn);
      }
    }
    this.id = this.subs.size ? this.deps.raf(this.tick) : 0;
  };
}

function browserDeps(): LoopDeps {
  if (typeof window === 'undefined' || typeof requestAnimationFrame === 'undefined')
    return { raf: () => 0, caf: () => undefined, now: () => 0 };
  return {
    raf: (cb) => requestAnimationFrame(cb),
    caf: (id) => cancelAnimationFrame(id),
    now: () => performance.now(),
    doc: document,
    reducedMotion: typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null,
  };
}

export const loop = new Loop(browserDeps());
