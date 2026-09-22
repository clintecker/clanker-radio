/**
 * Damped spring with hard end stops, integrated in fixed 4 ms sub-steps so it behaves the
 * same at 30, 60 or 120 Hz. `w` is natural frequency (rad/s), `z` damping ratio: z < 1
 * overshoots (moving-coil needle, detent knob), z = 1 is critically damped. When the
 * mass hits a stop it bounces back with `restitution` of its speed, like a needle on its pin.
 */

export interface SpringSpec {
  w: number;
  z: number;
  min?: number;
  max?: number;
  restitution?: number;
}

const SUBSTEP = 0.004;

export class Spring {
  x: number;
  v = 0;
  target: number;

  constructor(
    readonly spec: SpringSpec,
    x0 = 0,
  ) {
    this.x = x0;
    this.target = x0;
  }

  step(dt: number, reduced = false): number {
    const { w, z, min = -Infinity, max = Infinity, restitution = 0.28 } = this.spec;
    if (reduced) {
      this.x = Math.min(max, Math.max(min, this.target));
      this.v = 0;
      return this.x;
    }
    const n = Math.max(1, Math.ceil(dt / SUBSTEP));
    const h = dt / n;
    for (let i = 0; i < n; i++) {
      this.v += (w * w * (this.target - this.x) - 2 * z * w * this.v) * h;
      this.x += this.v * h;
      if (this.x < min) {
        this.x = min;
        this.v = -this.v * restitution;
      }
      if (this.x > max) {
        this.x = max;
        this.v = -this.v * restitution;
      }
    }
    return this.x;
  }

  /** An impulse through the chassis (relay thump). */
  kick(dv: number): void {
    this.v += dv;
  }

  snap(x: number): void {
    this.x = x;
    this.target = x;
    this.v = 0;
  }

  settled(eps = 1e-3): boolean {
    return Math.abs(this.x - this.target) < eps && Math.abs(this.v) < eps;
  }
}

/** Rotary detent: stiff spring, light damping, so it snaps and settles past the click. */
export const DETENT: SpringSpec = { w: Math.sqrt(1500), z: 0.42 };
