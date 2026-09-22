/**
 * Spectrum sampling for the signal strip. Pure-ish: given an analyser (or none)
 * returns 0..1 bar levels. Idle, it drifts a faint noise floor so the strip reads
 * as a powered receiver rather than a frozen decoration.
 */
export class Spectrum {
  private buffer: Uint8Array<ArrayBuffer> | null = null;
  private readonly noise: Float32Array;

  constructor(
    readonly bars = 48,
    private readonly idleStep = 0.03,
  ) {
    this.noise = new Float32Array(bars).map(() => Math.random());
  }

  levels(analyser: AnalyserNode | null): Float32Array {
    const out = new Float32Array(this.bars);
    if (analyser) {
      if (this.buffer?.length !== analyser.frequencyBinCount) this.buffer = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(this.buffer);
      const usable = Math.floor(this.buffer.length * 0.75); // drop the near-empty top octave
      for (let i = 0; i < this.bars; i++) {
        // Log-ish spacing so bass does not hog half the strip
        const lo = Math.floor(usable * Math.pow(i / this.bars, 1.6));
        const hi = Math.max(lo + 1, Math.floor(usable * Math.pow((i + 1) / this.bars, 1.6)));
        let sum = 0;
        for (let j = lo; j < hi; j++) sum += this.buffer[j] ?? 0;
        out[i] = sum / (hi - lo) / 255;
      }
      return out;
    }
    for (let i = 0; i < this.bars; i++) {
      const n = (this.noise[i] ?? 0) + (Math.random() - 0.5) * this.idleStep;
      this.noise[i] = Math.min(1, Math.max(0, n));
      out[i] = 0.04 + (this.noise[i] ?? 0) * 0.08;
    }
    return out;
  }
}
