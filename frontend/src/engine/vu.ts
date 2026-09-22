/**
 * VU meter maths. The needle is a spring tuned to VU ballistics (about 300 ms to reach
 * reference, ~4% overshoot). What drives it is either the real program, measured from an
 * AnalyserNode, or a model of the program when the stream cannot be analysed.
 */
import type { SpringSpec } from './spring';
import type { TrackKind } from '../lib/types';

export const VU_MAX = Math.pow(10, 3 / 20);
/** dB VU → needle position (0 = left end of scale, 1 = +3 VU). */
export const vuP = (db: number): number => Math.pow(10, db / 20) / VU_MAX;
export const VU_REST = -0.05;
export const VU_SPRING: SpringSpec = { w: 15, z: 0.72, min: VU_REST, max: 1.06, restitution: 0.28 };

/** Streams are mastered hot: program RMS near -14 dBFS reads 0 VU. */
export const DBFS_AT_0VU = -14;

/** RMS of a byte time-domain buffer (128 = silence) in dBFS; -Infinity for digital silence. */
export function rmsDbfs(buf: Uint8Array): number {
  let sum = 0;
  for (const b of buf) {
    const s = (b - 128) / 128;
    sum += s * s;
  }
  const rms = Math.sqrt(sum / Math.max(1, buf.length));
  return rms > 0 ? 20 * Math.log10(rms) : -Infinity;
}

/** Simulated program level in dB VU: a beat and phrase for music, syllables for speech. */
export class ProgramModel {
  private noise = 0;
  constructor(private readonly rnd: () => number = Math.random) {}

  db(t: number, kind: TrackKind): number {
    this.noise += ((this.rnd() - 0.5) * 2 - this.noise) * 0.08;
    if (kind === 'break') {
      const syl = Math.max(0, Math.sin(t * 2 * Math.PI * 3.6 + Math.sin(t * 1.3) * 2.2));
      const gate = Math.sin(t * 0.83) + Math.sin(t * 2.1) * 0.4 > -0.55;
      return gate ? -9 + 8 * syl + 2 * this.noise : -26;
    }
    const beat = Math.exp(-((t * 2.1) % 1) * 5);
    const phrase = 0.5 + 0.5 * Math.sin(t * 0.37) * Math.sin(t * 0.11 + 1);
    if (kind === 'bumper') return -5 + 5 * beat + 2.5 * this.noise;
    return -11 + 5.5 * beat + 5 * phrase + 2.2 * this.noise;
  }
}

/** How long an analyser may read pure silence while playing before we assume it is blind (CORS). */
export const BLIND_AFTER_S = 2;

interface AnalyserLike {
  fftSize: number;
  getByteTimeDomainData(buf: Uint8Array<ArrayBuffer>): void;
}

/**
 * Program level source. Prefers the real signal; if the analyser only ever reads digital
 * silence for BLIND_AFTER_S while audio is playing (a tainted cross-origin stream reads
 * as zeros), it falls back to the model for the rest of the session.
 */
export class ProgramLevel {
  private buf: Uint8Array<ArrayBuffer> | null = null;
  private silentFor = 0;
  private blind = false;
  readonly model: ProgramModel;

  constructor(rnd: () => number = Math.random) {
    this.model = new ProgramModel(rnd);
  }

  get source(): 'real' | 'simulated' {
    return this.blind ? 'simulated' : 'real';
  }

  /** dB VU at time t (s). `analyser` may be null (no Web Audio): simulated. */
  read(t: number, dt: number, kind: TrackKind, analyser: AnalyserLike | null): { db: number; real: boolean } {
    if (!analyser || this.blind) return { db: this.model.db(t, kind), real: false };
    if (this.buf?.length !== analyser.fftSize) this.buf = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(this.buf);
    const dbfs = rmsDbfs(this.buf);
    if (!Number.isFinite(dbfs)) {
      this.silentFor += dt;
      if (this.silentFor >= BLIND_AFTER_S) this.blind = true;
      return { db: this.blind ? this.model.db(t, kind) : -40, real: !this.blind };
    }
    this.silentFor = 0;
    return { db: dbfs - DBFS_AT_0VU, real: true };
  }

  /** New stream, new chance: forget a previous blind verdict. */
  reset(): void {
    this.silentFor = 0;
    this.blind = false;
  }
}
