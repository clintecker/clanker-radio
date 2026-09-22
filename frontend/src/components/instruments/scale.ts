/**
 * Printed meter scales. A ScaleSpec says where ticks and labels go (0..1 along a 96°
 * arc); the Meter component prints it. Compact mode (face narrower than 210 px) uses
 * fewer, larger marks so it stays legible on a phone.
 */
import { formatClock } from '../../lib/format';
import { vuP } from '../../engine/vu';

export const PX = 150;
export const PY = 160;
export const R = 118;
export const HALF = 48;
export const VIEW_W = 300;
export const VIEW_H = 184;
export const COMPACT_BELOW_PX = 210;

export interface Tick {
  p: number;
  major: boolean;
  red?: boolean;
}
export interface Label {
  p: number;
  text: string;
  red?: boolean;
}
export interface ScaleSpec {
  mark: string;
  foot: string;
  red: readonly [number, number] | null;
  ticks(compact: boolean): Tick[];
  labels(compact: boolean): Label[];
}

export const angleOf = (p: number): number => -HALF + 2 * HALF * p;

export function polar(p: number, r: number): [number, number] {
  const a = ((angleOf(p) - 90) * Math.PI) / 180;
  return [PX + r * Math.cos(a), PY + r * Math.sin(a)];
}

export function arc(p0: number, p1: number, r: number): string {
  const [x0, y0] = polar(p0, r);
  const [x1, y1] = polar(p1, r);
  return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
}

export const labelSize = (compact: boolean) => (compact ? 21 : 12.5);
export const labelRadius = (compact: boolean) => (compact ? R + 24 : R + 15);

/** Approximate printed width of a label in viewBox units (Martian Mono is ~0.62 em per glyph). */
export const labelWidth = (text: string, compact: boolean) => text.length * labelSize(compact) * 0.62;

/** True if any two neighbouring labels would overprint each other. */
export function labelsCollide(spec: ScaleSpec, compact: boolean): boolean {
  const ls = [...spec.labels(compact)].sort((a, b) => a.p - b.p);
  const r = labelRadius(compact);
  for (let i = 1; i < ls.length; i++) {
    const a = ls[i - 1],
      b = ls[i];
    if (!a || !b) continue;
    const [ax, ay] = polar(a.p, r);
    const [bx, by] = polar(b.p, r);
    const gap = Math.hypot(bx - ax, by - ay);
    if (gap < (labelWidth(a.text, compact) + labelWidth(b.text, compact)) / 2 + 2) return true;
  }
  return false;
}

const VU_MAJOR = [-20, -10, -7, -5, -3, 0, 3];
export const vuScale: ScaleSpec = {
  mark: 'VU',
  foot: '300 MS',
  red: [vuP(0), 1],
  ticks: (c) =>
    [-20, -15, -10, -7, -5, -4, -3, -2, -1, 0, 1, 2, 3]
      .filter((d) => !c || VU_MAJOR.includes(d))
      .map((d) => ({ p: vuP(d), major: VU_MAJOR.includes(d), red: d > 0 })),
  labels: (c) =>
    (c ? [-20, -5, 0, 3] : [-20, -10, -5, 0, 3]).map((d) => ({
      p: vuP(d),
      text: d > 0 ? `+${d}` : String(d),
      red: d > 0,
    })),
};

/** Track position in min:sec; the red arc marks the crossfade at the end. */
export function positionScale(durationSec: number, crossfadeSec: number): ScaleSpec {
  const d = durationSec > 0 ? durationSec : 0;
  return {
    mark: 'MIN·SEC',
    foot: 'TRACK',
    red: crossfadeSec > 0 && d > 0 ? [Math.max(0, 1 - crossfadeSec / d), 1] : null,
    ticks: () => Array.from({ length: 21 }, (_, i) => ({ p: i / 20, major: i % 5 === 0 })),
    labels: (c) => (c ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]).map((p) => ({ p, text: formatClock(d * p) })),
  };
}

export const carrierScale: ScaleSpec = {
  mark: '% CARRIER',
  foot: 'RF',
  red: [0, 0.2],
  ticks: () => Array.from({ length: 11 }, (_, i) => ({ p: i / 10, major: i % 2 === 0, red: i < 2 })),
  labels: (c) =>
    (c ? [0, 0.5, 1] : [0, 0.2, 0.4, 0.6, 0.8, 1]).map((p) => ({
      p,
      text: String(Math.round(p * 100)),
      red: p < 0.2,
    })),
};
