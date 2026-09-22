import { useEffect, useRef } from 'preact/hooks';
import { bus } from '../../engine/bus';
import { loop } from '../../engine/loop';
import type { PlayerState } from '../../lib/player';
import { Tri } from '../primitives/Legend';

export const LATCH_MAIN: Record<PlayerState, string> = {
  idle: 'Tune in',
  loading: 'Locking',
  playing: 'On air',
  error: 'No carrier',
};
export const LATCH_SUB: Record<PlayerState, string> = {
  idle: 'Press to listen live',
  loading: 'Finding the carrier',
  playing: 'Press to go dark',
  error: 'Stream refused. Press to retry',
};

const isOn = (s: PlayerState) => s === 'playing' || s === 'loading';

export interface LatchButtonProps {
  state: PlayerState;
  /** Overrides the sub-legend (e.g. "Hopping to 96k", "Buffering"). */
  sub?: string;
  note?: string;
  onPress: () => void;
}

/**
 * TUNE IN: a latching, illuminated push-button in a hazard-striped well. Going on strikes
 * the readout (flicker), thumps the meters and closes the relay; going off fades it down.
 * The cap lamp is a filament: fast warm-up, slow cool-down; it blinks while locking.
 */
export function LatchButton({ state, sub, note, onPress }: LatchButtonProps) {
  const btn = useRef<HTMLButtonElement>(null);
  const stateRef = useRef(state);
  const flash = useRef(0);

  useEffect(() => {
    const was = stateRef.current;
    stateRef.current = state;
    const now = performance.now();
    if (!isOn(was) && isOn(state)) {
      bus.power.up(now, loop.reduced);
      flash.current = 1;
      bus.thump('press');
    } else if (isOn(was) && !isOn(state)) {
      bus.power.down(now, loop.reduced);
    }
  }, [state]);

  useEffect(() => {
    let g = 0;
    let lastG = -1;
    return loop.add((dt, now) => {
      if (bus.power.step(now)) bus.thump('relay');
      const s = stateRef.current;
      const blink = Math.floor(now / 420) % 2 === 0;
      let target =
        s === 'playing'
          ? 1
          : s === 'loading'
            ? blink
              ? 0.55
              : 0.12
            : s === 'error'
              ? Math.floor(now / 260) % 2
                ? 0.5
                : 0
              : 0;
      if (flash.current > 0) {
        target = Math.max(target, flash.current);
        flash.current = Math.max(0, flash.current - dt * 9);
      }
      if (loop.reduced) g = s === 'loading' ? 0.55 : target;
      else g += (target - g) * (1 - Math.exp(-dt / (target > g ? 0.04 : 0.14)));
      if (Math.abs(g - lastG) > 0.004) {
        btn.current?.style.setProperty('--g', g.toFixed(3));
        lastG = g;
      }
    });
  }, []);

  return (
    <div class="ctl tune-wrap">
      <span class="engr ctl-title">
        <span>
          Listen
          <Tri zh="收听" id="Dengar" ru="Слушать" />
        </span>
        {note && <span class="engr-2">{note}</span>}
      </span>
      <div class="well">
        <button
          ref={btn}
          class="tune"
          type="button"
          aria-pressed={isOn(state)}
          data-state={state}
          data-tone={state === 'playing' ? 'red' : 'amber'}
          onClick={onPress}
        >
          <span class="glow" aria-hidden="true" />
          <span class="lens" aria-hidden="true" />
          <span class="main">{LATCH_MAIN[state]}</span>
          <span class="sub">{sub ?? LATCH_SUB[state]}</span>
        </button>
      </div>
    </div>
  );
}
