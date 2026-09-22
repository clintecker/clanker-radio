/**
 * Incandescent behaviour. A filament heats fast and cools slowly, so a lamp driven by a
 * square wave never quite reaches black. `Filament` is that envelope; `PowerSequence`
 * is the readout's power-up flicker (a VFD striking) and fade-down.
 */

export const WARM_TAU = 0.04;
export const COOL_TAU = 0.14;

export class Filament {
  value = 0;
  target = 0;

  step(dt: number, reduced = false): number {
    if (reduced) return (this.value = this.target);
    const tau = this.target > this.value ? WARM_TAU : COOL_TAU;
    this.value += (this.target - this.value) * (1 - Math.exp(-dt / tau));
    return this.value;
  }
}

/** [ms since power-on, luminance]: strike, sag, re-strike, settle. */
export const POWER_FLICKER: readonly (readonly [number, number])[] = [
  [0, 0.5],
  [50, 0.2],
  [95, 0.9],
  [140, 0.35],
  [190, 1],
  [240, 0.6],
  [300, 1],
  [380, 0.82],
  [470, 1],
];
export const STANDBY_LUM = 0.74;
/** When the relay closes and thumps the meters. */
export const THUMP_AT_MS = 230;
const SETTLE_MS = 520;
const DOWN_MS = 480;

export function flickerLum(ms: number): number {
  if (ms > SETTLE_MS) return 1;
  let lum = 1;
  for (const [t, v] of POWER_FLICKER) if (ms >= t) lum = v;
  return lum;
}

export class PowerSequence {
  lum = STANDBY_LUM;
  private dir: -1 | 0 | 1 = 0;
  private t0 = 0;
  private from = STANDBY_LUM;
  private thumped = false;

  get active(): boolean {
    return this.dir !== 0;
  }

  up(now: number, reduced = false): void {
    if (reduced) {
      this.dir = 0;
      this.lum = 1;
      return;
    }
    this.dir = 1;
    this.t0 = now;
    this.thumped = false;
  }

  down(now: number, reduced = false): void {
    if (reduced) {
      this.dir = 0;
      this.lum = STANDBY_LUM;
      return;
    }
    this.dir = -1;
    this.t0 = now;
    this.from = this.lum;
  }

  /** Advance to `now` (ms). Returns true on the one frame the relay thumps. */
  step(now: number): boolean {
    if (this.dir === 1) {
      const t = now - this.t0;
      this.lum = flickerLum(t);
      let thump = false;
      if (!this.thumped && t > THUMP_AT_MS) thump = this.thumped = true;
      if (t > 900) this.dir = 0;
      return thump;
    }
    if (this.dir === -1) {
      const t = Math.min(1, Math.max(0, (now - this.t0) / DOWN_MS));
      const e = 1 - Math.pow(1 - t, 3);
      this.lum = this.from + (STANDBY_LUM - this.from) * e;
      if (t >= 1) this.dir = 0;
    }
    return false;
  }
}
