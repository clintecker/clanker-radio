import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { KIND_LAMP } from './kind';

// vitest runs from frontend/
const css = readFileSync('src/design/tokens.css', 'utf8');

const tokens: Record<string, string> = Object.fromEntries(
  [...css.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})\b/gi)].map((m) => [m[1], m[2]]),
);

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

// [text token, background token, minimum ratio]. Small text everywhere, so 4.5 unless noted.
const PAIRS: [string, string, number][] = [
  ['engrave', 'panel', 4.5],
  ['engrave-2', 'panel', 4.5],
  ['legend-k', 'panel', 3], // decorative trilingual sub-legend, aria-hidden
  ['legend-k', 'glass', 4.5],
  ['amber', 'glass', 4.5],
  ['amber-dim', 'glass', 4.5],
  ['mag', 'glass', 4.5],
  ['mag-dim', 'glass', 4.5],
  ['cyan', 'glass', 4.5],
  ['cyan-dim', 'glass', 4.5],
  ['white', 'glass', 7],
  ['ink', 'face', 7],
  ['scale-red', 'face', 3], // printed red arc + large numerals
];

describe('design tokens', () => {
  it('parses every token the pairs need', () => {
    for (const [a, b] of PAIRS) {
      expect(tokens[a], a).toMatch(/^#/);
      expect(tokens[b], b).toMatch(/^#/);
    }
  });
  it.each(PAIRS)('%s on %s ≥ %s:1', (fg, bg, min) => {
    expect(contrast(tokens[fg] ?? '', tokens[bg] ?? '')).toBeGreaterThanOrEqual(min);
  });
  it('maps every content kind to a lamp colour', () => {
    expect(KIND_LAMP).toEqual({ music: 'amber', break: 'magenta', bumper: 'cyan', unknown: 'amber' });
  });
});
