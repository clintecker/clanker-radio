/**
 * VFD title refresh: when a new title arrives the tube re-strikes left to right, blocks
 * first, then random segments, then the real glyph. Works on code points so CJK and
 * Cyrillic resolve per character. Pure functions + a tiny stateful driver.
 */

export const GLYPHS = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789#%&*+=/<>';
export const HEX = '0123456789ABCDEF';
/** VFD refresh ~30 Hz. */
export const FRAME_MS = 34;

export const scrambleDuration = (n: number): number => 180 + Math.min(420, n * 12);

export function scrambleFrame(chars: readonly string[], t: number, dur: number, rnd: () => number): string {
  const n = chars.length;
  let out = '';
  for (let i = 0; i < n; i++) {
    const ch = chars[i] ?? '';
    const resolveAt = 60 + (i / Math.max(1, n - 1)) * dur;
    if (t >= resolveAt || /\s/.test(ch)) out += ch;
    else if (t < resolveAt - 260) out += i % 3 === 0 ? '█' : '░';
    else out += GLYPHS[(rnd() * GLYPHS.length) | 0] ?? '#';
  }
  return out;
}

export class Scrambler {
  private chars: string[] = [];
  private t0 = 0;
  private dur = 0;
  private last = -Infinity;
  private active = false;
  text = '';

  constructor(private readonly rnd: () => number = Math.random) {}

  get running(): boolean {
    return this.active;
  }

  /** Begin resolving `text` at `now` (ms). With reduced motion it resolves immediately. */
  start(text: string, now: number, reduced = false): void {
    this.text = text;
    this.chars = Array.from(text);
    this.t0 = now;
    this.dur = scrambleDuration(this.chars.length);
    this.last = -Infinity;
    this.active = !reduced;
  }

  /** Text to show at `now`, or null when nothing changed since the last frame. */
  frame(now: number): string | null {
    if (!this.active) return null;
    const t = now - this.t0;
    if (t >= this.dur + 60) {
      this.active = false;
      return this.text;
    }
    if (now - this.last < FRAME_MS) return null;
    this.last = now;
    return scrambleFrame(this.chars, t, this.dur, this.rnd);
  }
}

/** Session key: three groups of four hex digits. */
export function newKey(rnd: () => number = Math.random): string {
  return Array.from({ length: 3 }, () => Array.from({ length: 4 }, () => HEX[(rnd() * 16) | 0]).join('')).join('·');
}

/** Re-key animation: each digit settles 40 ms after the previous; separators never scramble. */
export function rekeyFrame(key: string, t: number, rnd: () => number = Math.random): string {
  return Array.from(key)
    .map((ch, i) => (ch === '·' || t > 120 + i * 40 ? ch : (HEX[(rnd() * 16) | 0] ?? '0')))
    .join('');
}
export const REKEY_MS = 700;
