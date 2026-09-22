/**
 * Procedural materials: bead-blasted gunmetal with grime, a rain film, and a scrape mask
 * for stickers. Drawn once on a canvas, turned into data URIs, cached for the session and
 * exposed as CSS custom properties (--tex, --rain, --scrape). No image files shipped.
 * Deterministic (seeded) so every visit, and every screenshot, gets the same plate.
 */

export interface Textures {
  tex: string;
  rain: string;
  scrape: string;
}

const CACHE_KEY = 'console.textures.v1';

type Ctx = CanvasRenderingContext2D;

function canvas(w: number, h: number): [HTMLCanvasElement, Ctx] | null {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const g = c.getContext('2d');
  return g ? [c, g] : null;
}

export function seeded(seed: number): () => number {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

export function generateTextures(): Textures | null {
  const rnd = seeded(1337);
  const plate = canvas(200, 200);
  const rainC = canvas(260, 340);
  const scrapeC = canvas(140, 160);
  if (!plate || !rainC || !scrapeC) return null;

  // faceplate: fine grain, faint horizontal machining, grime blooms and scratches
  let [c, g] = plate;
  for (let i = 0; i < 90; i++) {
    g.fillStyle = `rgba(${rnd() > 0.5 ? '255,255,255' : '0,0,0'},${0.015 + rnd() * 0.03})`;
    g.fillRect(0, (rnd() * 200) | 0, 200, 1);
  }
  for (let i = 0; i < 14; i++) {
    const x = rnd() * 200,
      y = rnd() * 200,
      r = 10 + rnd() * 30;
    for (const ox of [-200, 0, 200])
      for (const oy of [-200, 0, 200]) {
        const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
        gr.addColorStop(0, `rgba(10,8,4,${0.08 + rnd() * 0.08})`);
        gr.addColorStop(1, 'rgba(10,8,4,0)');
        g.fillStyle = gr;
        g.fillRect(x + ox - r, y + oy - r, r * 2, r * 2);
      }
  }
  g.lineWidth = 0.6;
  for (let i = 0; i < 16; i++) {
    const x = rnd() * 200,
      y = rnd() * 200,
      a = rnd() * Math.PI,
      l = 6 + rnd() * 24;
    g.strokeStyle = `rgba(200,220,230,${0.05 + rnd() * 0.07})`;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l);
    g.stroke();
  }
  for (let i = 0; i < 3600; i++) {
    g.fillStyle = rnd() > 0.5 ? `rgba(255,255,255,${0.03 + rnd() * 0.05})` : `rgba(0,0,0,${0.06 + rnd() * 0.1})`;
    g.fillRect((rnd() * 200) | 0, (rnd() * 200) | 0, 1, 1);
  }
  const tex = c.toDataURL('image/png');

  // rain film: thin slanted streaks and a few beads catching the city light
  [c, g] = rainC;
  for (let i = 0; i < 70; i++) {
    const x = rnd() * 260,
      y = rnd() * 340,
      l = 10 + rnd() * 40;
    g.strokeStyle = `rgba(${rnd() > 0.7 ? '255,120,190' : '170,230,240'},${0.03 + rnd() * 0.06})`;
    g.lineWidth = 0.7;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x - l * 0.12, y + l);
    g.stroke();
  }
  for (let i = 0; i < 26; i++) {
    const x = rnd() * 260,
      y = rnd() * 340,
      r = 0.8 + rnd() * 1.6;
    g.fillStyle = 'rgba(200,240,255,.08)';
    g.beginPath();
    g.arc(x, y, r, 0, 7);
    g.fill();
  }
  const rain = c.toDataURL('image/png');

  // scrape mask: mostly opaque with scraped-off holes
  [c, g] = scrapeC;
  g.fillStyle = '#000';
  g.fillRect(0, 0, 140, 160);
  g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 40; i++) {
    const x = rnd() * 140,
      y = rnd() * 160;
    g.globalAlpha = 0.4 + rnd() * 0.6;
    g.beginPath();
    g.ellipse(x, y, 2 + rnd() * 12, 1 + rnd() * 4, rnd() * 3, 0, 7);
    g.fill();
  }
  const scrape = c.toDataURL('image/png');
  return { tex, rain, scrape };
}

function isTextures(v: unknown): v is Textures {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  return [o.tex, o.rain, o.scrape].every((s) => typeof s === 'string' && s.startsWith('data:image/png'));
}

/** Apply the materials to an element (normally <html>). A bare plate is fine if canvas is unavailable. */
export function applyTextures(el: HTMLElement = document.documentElement): boolean {
  let t: Textures | null = null;
  try {
    const cached: unknown = JSON.parse(sessionStorage.getItem(CACHE_KEY) ?? 'null');
    if (isTextures(cached)) t = cached;
  } catch {
    /* storage blocked or corrupt */
  }
  if (!t) {
    try {
      t = generateTextures();
    } catch {
      t = null;
    }
    if (!t) return false;
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(t));
    } catch {
      /* quota or blocked; regenerate next time */
    }
  }
  el.style.setProperty('--tex', `url(${t.tex})`);
  el.style.setProperty('--rain', `url(${t.rain})`);
  el.style.setProperty('--scrape', `url(${t.scrape})`);
  return true;
}
