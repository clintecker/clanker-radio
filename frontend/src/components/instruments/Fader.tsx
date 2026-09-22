import { useId } from 'preact/hooks';
import { Tri } from '../primitives/Legend';

export interface FaderProps {
  /** 0..100 */
  value: number;
  onInput: (v: number) => void;
  /** iOS ignores element volume; show the fader parked with a note instead of a dead control. */
  disabled?: boolean;
}

/** Long-throw fader on a native range input, so keyboard and AT get a real slider. */
export function Fader({ value, onInput, disabled }: FaderProps) {
  const id = useId();
  return (
    <div class="ctl fader">
      <label class="engr ctl-title" for={id}>
        <span>
          Volume
          <Tri zh="音量" id="Volume" ru="Громк." />
        </span>
        <output class="num" for={id}>
          {disabled ? 'device' : value}
        </output>
      </label>
      <div class="body">
        <div class="scale num" aria-hidden="true">
          {[0, 2, 4, 6, 8, 10].map((n) => (
            <span key={n}>{n}</span>
          ))}
        </div>
        <div class="ticks" aria-hidden="true" />
        <input
          id={id}
          type="range"
          min="0"
          max="100"
          value={value}
          disabled={disabled}
          aria-label="Listening level"
          aria-describedby={disabled ? `${id}-n` : undefined}
          onInput={(e) => onInput(Number(e.currentTarget.value))}
        />
        <div class="ticks lo" aria-hidden="true" />
        {disabled && (
          <p class="sr" id={`${id}-n`}>
            Use your device's volume buttons.
          </p>
        )}
      </div>
    </div>
  );
}
