import type { ComponentChildren } from 'preact';
import { useEffect, useId, useRef, useState } from 'preact/hooks';
import { bus } from '../../engine/bus';
import { loop } from '../../engine/loop';
import type { Spring } from '../../engine/spring';
import { Tri, type TriProps } from '../primitives/Legend';
import {
  COMPACT_BELOW_PX,
  PX,
  PY,
  R,
  VIEW_H,
  VIEW_W,
  angleOf,
  arc,
  labelRadius,
  labelSize,
  polar,
  type ScaleSpec,
} from './scale';

const INK = '#15201E';
const SRED = '#D0204F';
const SHAFT = 'M148.5 178 L151.5 178 L150.5 34 L149.5 34 Z';

/** Printed face: arc, red zone, ticks, numerals, maker's mark, holographic film. Pure SVG. */
function ScaleFace({ spec, compact }: { spec: ScaleSpec; compact: boolean }) {
  const c = compact;
  const fs = labelSize(c);
  const lr = labelRadius(c);
  const [pinX, pinY] = polar(-0.055, R - 22);
  return (
    <g>
      <path d={arc(0, 1, R)} fill="none" stroke={INK} stroke-width={c ? 2.4 : 1.6} />
      {spec.red && <path d={arc(spec.red[0], spec.red[1], R + 4)} fill="none" stroke={SRED} stroke-width={c ? 8 : 6} />}
      {spec.ticks(c).map((t) => {
        const [x0, y0] = polar(t.p, R);
        const [x1, y1] = polar(t.p, R - (t.major ? (c ? 16 : 13) : c ? 8 : 6));
        return (
          <line
            key={t.p}
            x1={x0.toFixed(2)}
            y1={y0.toFixed(2)}
            x2={x1.toFixed(2)}
            y2={y1.toFixed(2)}
            stroke={t.red ? SRED : INK}
            stroke-width={t.major ? (c ? 2.6 : 1.8) : c ? 1.6 : 1}
          />
        );
      })}
      {spec.labels(c).map((l) => {
        const [x, y] = polar(l.p, lr);
        return (
          <text
            key={l.p}
            class="scale-num"
            x={x.toFixed(1)}
            y={(y + fs * 0.36).toFixed(1)}
            text-anchor="middle"
            font-size={fs}
            fill={l.red ? SRED : INK}
          >
            {l.text}
          </text>
        );
      })}
      <text class="scale-mark" x={PX} y={c ? 120 : 112} text-anchor="middle" font-size={c ? 26 : 19} fill={INK}>
        {spec.mark}
      </text>
      {/* hologram layer, slightly out of register */}
      <g opacity=".55" transform="translate(1.2 -1)">
        <path
          d={arc(0, 1, R + (c ? 34 : 26))}
          fill="none"
          stroke="#0FB8AA"
          stroke-width={c ? 1.6 : 1}
          stroke-dasharray="1 4"
        />
        {spec.red && (
          <path
            d={arc(spec.red[0], spec.red[1], R + (c ? 34 : 26))}
            fill="none"
            stroke="#FF2E88"
            stroke-width={c ? 3 : 2}
          />
        )}
      </g>
      <circle cx={pinX.toFixed(1)} cy={pinY.toFixed(1)} r={c ? 3.6 : 2.6} fill="#1a1712" />
      {!c && (
        <>
          <text class="scale-foot" x="12" y="176" font-size="7" fill={INK}>
            MIL-SURPLUS · 军品
          </text>
          <text class="scale-foot" x="288" y="172" text-anchor="end" font-size="7" fill={INK}>
            {spec.foot}
          </text>
        </>
      )}
    </g>
  );
}

export interface MeterProps {
  title: string;
  tri: TriProps;
  spec: ScaleSpec;
  /** The needle. Owned by the caller, stepped here once per frame. */
  spring: Spring;
  caption: ComponentChildren;
  /** Needle kick when TUNE is pressed / when the relay closes. */
  thump?: { press: number; relay: number };
  /** Accessible value, updated at data rate (not per frame). */
  value: number;
  min?: number;
  max?: number;
  valueText: string;
  class?: string;
}

/** Moving-coil panel meter: printed face, needle with cast shadow, bakelite hub. */
export function Meter({
  title,
  tri,
  spec,
  spring,
  caption,
  thump,
  value,
  min = 0,
  max = 1,
  valueText,
  class: cls,
}: MeterProps) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const svgRef = useRef<SVGSVGElement>(null);
  const needle = useRef<SVGGElement>(null);
  const shadow = useRef<SVGGElement>(null);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((es) => {
      const w = es[0]?.contentRect.width ?? VIEW_W;
      setCompact(w > 0 && w < COMPACT_BELOW_PX);
    });
    ro.observe(svg);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let lastA = NaN;
    const off = loop.add((dt) => {
      spring.step(dt, loop.reduced);
      const a = angleOf(Math.min(1.06, Math.max(-0.08, spring.x)));
      if (Math.abs(a - lastA) > 0.02) {
        const tr = `rotate(${a.toFixed(2)} ${PX} ${PY})`;
        needle.current?.setAttribute('transform', tr);
        shadow.current?.setAttribute('transform', tr);
        lastA = a;
      }
    });
    const offThump = thump
      ? bus.onThump((kind) => !loop.reduced && spring.kick(kind === 'press' ? thump.press : thump.relay))
      : undefined;
    return () => {
      off();
      offThump?.();
    };
  }, [spring, thump]);

  const initial = `rotate(${angleOf(spring.x).toFixed(2)} ${PX} ${PY})`;
  return (
    <div
      class={`meter${cls ? ` ${cls}` : ''}`}
      role="meter"
      aria-label={title}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value * 100) / 100}
      aria-valuetext={valueText}
    >
      <div class="engr meter-title" aria-hidden="true">
        {title}
        <Tri {...tri} />
      </div>
      <div class="bezel">
        <div class="face">
          <div class="holo" />
          <svg ref={svgRef} viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} aria-hidden="true" focusable="false">
            <defs>
              <filter id={`b${id}`} x="-50%" y="-10%" width="200%" height="120%">
                <feGaussianBlur stdDeviation="1.4" />
              </filter>
              <radialGradient id={`h${id}`} cx=".36" cy=".3" r=".75">
                <stop offset="0" stop-color="#8C979E" />
                <stop offset=".35" stop-color="#2A3136" />
                <stop offset="1" stop-color="#0C0806" />
              </radialGradient>
            </defs>
            <ScaleFace spec={spec} compact={compact} />
            <g transform="translate(3.5 5)" filter={`url(#b${id})`} opacity=".32">
              <g ref={shadow} transform={initial}>
                <path d={SHAFT} fill="#000" />
                <rect x="145.5" y="168" width="9" height="10" rx="1.5" fill="#000" />
              </g>
            </g>
            <g ref={needle} transform={initial} class="needle">
              <rect x="145.5" y="168" width="9" height="10" rx="1.5" fill="#17130E" />
              <path d={SHAFT} fill="#17130E" />
              <path d="M149.5 34 L150.5 34 L150.85 60 L149.15 60 Z" fill="#FF2E88" />
            </g>
            <circle cx={PX + 2} cy={PY + 3} r="15" fill="rgba(0,0,0,.28)" filter={`url(#b${id})`} />
            <circle cx={PX} cy={PY} r="14.5" fill={`url(#h${id})`} />
            <ellipse
              cx={PX - 4.5}
              cy={PY - 5.5}
              rx="5"
              ry="3"
              fill="rgba(255,255,255,.22)"
              transform={`rotate(-35 ${PX - 4.5} ${PY - 5.5})`}
            />
            <circle cx={PX} cy={PY} r="3.2" fill="#E8C21A" stroke="#4a3d05" stroke-width=".8" />
          </svg>
        </div>
      </div>
      <p class="mcap engr-2">{caption}</p>
    </div>
  );
}
