import type { Player } from '../lib/player';

/**
 * The signal strip: a bar-graph spectrum of what the listener is actually hearing.
 *
 * While tuned in it is driven by a Web Audio analyser on the stream. Idle, it shows
 * a faint, slowly drifting noise floor so the page reads as a receiver that is
 * powered on but not tuned, rather than a frozen decoration.
 */
export class SignalDisplay {
  private readonly ctx: CanvasRenderingContext2D;
  private analyser: AnalyserNode | null = null;
  private buffer: Uint8Array<ArrayBuffer> | null = null;
  private raf = 0;
  private readonly bars = 48;
  private readonly noise = new Float32Array(this.bars).map(() => Math.random());
  private readonly reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly player: Player,
  ) {
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas 2d unsupported');
    this.ctx = ctx;
    player.subscribe((snap) => {
      if (snap.state === 'playing' && !this.analyser) this.analyser = player.getAnalyser();
    });
    new ResizeObserver(() => this.resize()).observe(canvas);
    this.resize();
    document.addEventListener('visibilitychange', () => (document.hidden ? this.pause() : this.start()));
    this.start();
  }

  private resize(): void {
    const dpr = window.devicePixelRatio || 1;
    const { width, height } = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.max(1, Math.round(width * dpr));
    this.canvas.height = Math.max(1, Math.round(height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  start(): void {
    if (this.raf) return;
    const frame = () => {
      this.draw();
      this.raf = requestAnimationFrame(frame);
    };
    this.raf = requestAnimationFrame(frame);
  }

  pause(): void {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private levels(): Float32Array {
    const live = this.player.snapshot().state === 'playing' && this.analyser;
    const out = new Float32Array(this.bars);
    if (live && this.analyser) {
      if (this.buffer?.length !== this.analyser.frequencyBinCount) {
        this.buffer = new Uint8Array(this.analyser.frequencyBinCount);
      }
      this.analyser.getByteFrequencyData(this.buffer);
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
    // Idle noise floor: random walk, tiny amplitude.
    const step = this.reduceMotion ? 0 : 0.03;
    for (let i = 0; i < this.bars; i++) {
      const n = (this.noise[i] ?? 0) + (Math.random() - 0.5) * step;
      this.noise[i] = Math.min(1, Math.max(0, n));
      out[i] = 0.04 + (this.noise[i] ?? 0) * 0.08;
    }
    return out;
  }

  private draw(): void {
    const { width, height } = this.canvas.getBoundingClientRect();
    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);
    const levels = this.levels();
    const gap = 2;
    const barW = (width - gap * (this.bars - 1)) / this.bars;
    const live = this.player.snapshot().state === 'playing';
    const color =
      getComputedStyle(this.canvas)
        .getPropertyValue(live ? '--phosphor' : '--phosphor-dim')
        .trim() || '#7fff7f';
    ctx.fillStyle = color;
    ctx.globalAlpha = live ? 0.95 : 0.55;
    for (let i = 0; i < this.bars; i++) {
      const h = Math.max(1, (levels[i] ?? 0) * height);
      ctx.fillRect(i * (barW + gap), height - h, barW, h);
    }
    ctx.globalAlpha = 1;
  }
}
