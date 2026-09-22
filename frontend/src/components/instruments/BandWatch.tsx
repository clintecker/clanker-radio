import { useEffect, useRef } from 'preact/hooks';
import { bus } from '../../engine/bus';
import { loop } from '../../engine/loop';
import type { Carrier } from '../modules/select';

/** Where each feed's carrier sits on the printed band scale (87.5 · 96 · 128 · 192). */
export const CARRIER_POS: Record<number, number> = { 96: 0.25, 128: 0.5, 192: 0.75 };

export interface BandWatchProps {
  carrier: Carrier;
  /** Bitrates reported by Icecast; one carrier each. */
  carriers: readonly number[];
  selected: number;
  analyser: () => AnalyserNode | null;
}

type Surface = HTMLCanvasElement | OffscreenCanvas;

function lowPower(): boolean {
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  return (nav.deviceMemory !== undefined && nav.deviceMemory <= 2) || nav.connection?.saveData === true;
}

/**
 * Band watch: spectrum + waterfall of the pirate band, driven by real state. The selected
 * feed's carrier is brightest and swells with the program (real analyser sidebands when the
 * stream can be read); a corp jammer sweeps the band while reconnecting; the band goes to
 * noise when the carrier is lost. ~20 fps on the shared loop, 10 on low-power devices,
 * 2 with reduced motion, paused off-screen.
 */
export function BandWatch({ carrier, carriers, selected, analyser }: BandWatchProps) {
  const cv = useRef<HTMLCanvasElement>(null);
  const props = useRef({ carrier, carriers, selected, analyser });
  props.current = { carrier, carriers, selected, analyser };

  useEffect(() => {
    const canvas = cv.current;
    const g = canvas?.getContext('2d');
    if (!canvas || !g) return;
    let W = 0,
      H = 0,
      dpr = 1;
    const wf: Surface =
      typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(1, 1) : document.createElement('canvas');
    const wg = wf.getContext('2d');
    if (!wg) return;
    let freq: Uint8Array<ArrayBuffer> | null = null;
    const period = lowPower() ? 100 : 50;
    let last = 0;

    const draw = (t: number) => {
      if (!W) return;
      const { carrier: conn, carriers: cs, selected: sel, analyser: tap } = props.current;
      const sh = Math.round(H * 0.56),
        step = Math.round(3 * dpr),
        n = Math.floor(W / step);
      const lvl = Math.min(1, Math.max(0, bus.level));
      const selPos = CARRIER_POS[sel] ?? 0.5;
      const marks = (cs.length ? cs : [96, 128, 192]).map((b) => CARRIER_POS[b]).filter((p) => p !== undefined);
      const a = tap();
      if (a && lvl > 0.02) {
        if (freq?.length !== a.frequencyBinCount) freq = new Uint8Array(a.frequencyBinCount);
        a.getByteFrequencyData(freq);
      } else freq = null;
      const jx = ((t * 0.28) % 1.3) - 0.15;
      wg.globalCompositeOperation = 'copy';
      wg.drawImage(wf, 0, dpr);
      wg.globalCompositeOperation = 'source-over';
      g.clearRect(0, 0, W, H);
      for (let i = 0; i < n; i++) {
        const f = (i + 0.5) / n;
        let v = 0.05 + Math.random() * 0.05,
          jam = 0;
        if (conn === 'nosignal') v = 0.18 + Math.random() * 0.42;
        else {
          for (const c of marks) {
            const isSel = c === selPos;
            const d = (f - c) / (isSel ? 0.012 + lvl * 0.01 : 0.009);
            let amp = (isSel ? 0.62 + lvl * 0.3 : 0.34) * Math.exp(-d * d);
            if (isSel && lvl > 0.05) {
              const off = Math.abs(f - c) / 0.06;
              if (freq && off < 1) {
                // real sidebands: the programme's spectrum mirrored either side of the carrier
                const bin = Math.floor(off * freq.length * 0.7);
                amp = Math.max(amp, ((freq[bin] ?? 0) / 255) * 0.55 * (1 - off * 0.5));
              } else amp += 0.16 * lvl * Math.exp(-Math.pow((f - c) / 0.05, 2)) * Math.random();
            }
            if (conn === 'reconnecting') amp *= 0.35 + 0.3 * Math.random();
            v = Math.max(v, amp * (1 + bus.pulse * 0.35));
          }
          if (conn === 'reconnecting') {
            const d = (f - jx) / 0.06;
            jam = Math.exp(-d * d) * (0.7 + 0.3 * Math.random());
            if (Math.random() < 0.04) jam = Math.max(jam, 0.4 * Math.random());
            v = Math.max(v, jam);
          }
        }
        v = Math.min(1, v);
        const hot = jam > 0.2 || conn === 'nosignal';
        const h = Math.max(dpr, v * (sh - 18 * dpr));
        g.fillStyle = hot ? `rgba(255,46,136,${0.35 + v * 0.65})` : `rgba(62,242,224,${0.25 + v * 0.75})`;
        g.fillRect(i * step, sh - h, step - dpr, h);
        wg.fillStyle = hot ? `rgba(255,46,136,${v * v * 0.95})` : `rgba(62,242,224,${Math.max(0, v - 0.12) * 1.1})`;
        wg.fillRect(i * step, 0, step, dpr);
      }
      g.drawImage(wf, 0, sh);
      g.fillStyle = 'rgba(62,242,224,.18)';
      g.fillRect(0, sh - dpr, W, dpr);
    };

    const size = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      W = Math.max(1, Math.round(canvas.clientWidth * dpr));
      H = Math.max(1, Math.round(canvas.clientHeight * dpr));
      canvas.width = W;
      canvas.height = H;
      wf.width = W;
      wf.height = Math.max(1, H - Math.round(H * 0.56));
      for (let i = 0; i < 50; i++) draw(i * 0.05); // pre-fill the waterfall so it never starts blank
    };
    size();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(size) : null;
    ro?.observe(canvas);

    let off: (() => void) | null = null;
    const run = () => {
      off ??= loop.add((_, now) => {
        if (now - last < (loop.reduced ? 500 : period)) return;
        last = now;
        draw(now / 1000);
      });
    };
    const stop = () => {
      off?.();
      off = null;
    };
    let io: IntersectionObserver | null = null;
    if (typeof IntersectionObserver !== 'undefined') {
      io = new IntersectionObserver((es) => (es.some((e) => e.isIntersecting) ? run() : stop()));
      io.observe(canvas);
    } else run();
    return () => {
      stop();
      ro?.disconnect();
      io?.disconnect();
    };
  }, []);

  return <canvas ref={cv} aria-hidden="true" />;
}
