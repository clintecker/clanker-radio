import { useEffect, useMemo, useRef } from 'preact/hooks';
import { loop } from '../../engine/loop';
import { DETENT, Spring } from '../../engine/spring';
import { Lamp } from '../primitives/Lamp';
import { Tri, type TriProps } from '../primitives/Legend';

export interface RotaryOption {
  value: string;
  label: string;
}

export interface RotarySwitchProps {
  legend: string;
  tri: TriProps;
  name: string;
  options: readonly RotaryOption[];
  value: string;
  onChange: (value: string) => void;
}

const SWEEP = 52;
export const detentAngle = (i: number, n: number) => (n <= 1 ? 0 : -SWEEP + (2 * SWEEP * i) / (n - 1));

/**
 * Three-position rotary: a native radio group (arrow keys, AT semantics) printed around a
 * knurled knob that springs into each detent. Clicking the knob steps to the next position.
 */
export function RotarySwitch({ legend, tri, name, options, value, onChange }: RotarySwitchProps) {
  const idx = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );
  const knob = useRef<HTMLDivElement>(null);
  const radios = useRef<(HTMLInputElement | null)[]>([]);
  const spring = useMemo(() => new Spring(DETENT, detentAngle(idx, options.length)), []); // initial only
  spring.target = detentAngle(idx, options.length);

  useEffect(() => {
    let last = NaN;
    return loop.add((dt) => {
      const a = spring.step(dt, loop.reduced);
      if (!(Math.abs(a - last) <= 0.05)) {
        // NaN-safe: first frame always writes
        if (knob.current) knob.current.style.transform = `rotate(${a.toFixed(2)}deg)`;
        last = a;
      }
    });
  }, [spring]);

  const step = () => {
    const next = options[(idx + 1) % options.length];
    if (!next) return;
    onChange(next.value);
    radios.current[(idx + 1) % options.length]?.focus({ preventScroll: true });
  };

  return (
    <fieldset class="ctl rot">
      <legend class="engr">
        {legend}
        <Tri {...tri} />
      </legend>
      <div class="dial">
        {options.map((o, i) => (
          <label key={o.value} class={`pos p${i}`}>
            <input
              ref={(el) => void (radios.current[i] = el)}
              type="radio"
              name={name}
              value={o.value}
              checked={i === idx}
              onChange={(e) => e.currentTarget.checked && onChange(o.value)}
            />
            <Lamp colour="amber" on={i === idx} size="xs" />
            <span class="engr">{o.label}</span>
          </label>
        ))}
        <div class="knob-seat" aria-hidden="true">
          <div class="knob" ref={knob} onClick={step} style={{ transform: `rotate(${spring.x.toFixed(2)}deg)` }}>
            <div class="cap" />
            <div class="ptr" />
          </div>
          <div class="knob-light" />
        </div>
      </div>
    </fieldset>
  );
}
