import { useEffect, useRef } from 'preact/hooks';
import { Spectrum } from '../lib/spectrum';
import { player, playerState } from '../state';

/**
 * The signal strip: a bar-graph spectrum of what the listener is actually hearing,
 * driven by a Web Audio analyser while tuned in and a faint noise floor when idle.
 */
export function Signal() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const live = playerState.value?.state === 'playing';

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const spectrum = new Spectrum(48, reduceMotion ? 0 : 0.03);
    let raf = 0;
    let analyser: AnalyserNode | null = null;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    const draw = () => {
      const playing = playerState.value?.state === 'playing';
      if (playing && !analyser) analyser = player?.getAnalyser() ?? null;
      const { width, height } = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, width, height);
      const levels = spectrum.levels(playing ? analyser : null);
      const gap = 2;
      const barW = (width - gap * (spectrum.bars - 1)) / spectrum.bars;
      ctx.fillStyle = playing ? '#7fff7f' : '#4a9a4a';
      ctx.globalAlpha = playing ? 0.95 : 0.55;
      for (let i = 0; i < spectrum.bars; i++) {
        const h = Math.max(1, (levels[i] ?? 0) * height);
        ctx.fillRect(i * (barW + gap), height - h, barW, h);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    };
    const start = () => {
      if (!raf) raf = requestAnimationFrame(draw);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };
    const onVisibility = () => (document.hidden ? stop() : start());
    document.addEventListener('visibilitychange', onVisibility);
    start();
    return () => {
      stop();
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, []);

  return <canvas ref={canvasRef} class="block w-full h-11 mt-3.5" aria-hidden="true" data-live={live} />;
}
