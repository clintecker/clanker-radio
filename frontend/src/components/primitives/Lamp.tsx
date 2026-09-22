import type { LampColour } from '../../design/kind';

export interface LampProps {
  colour?: LampColour;
  on: boolean;
  size?: 'xs' | 'sm' | 'md';
  class?: string;
}

/** Incandescent indicator. The filament lag (fast on, slow off) is CSS; blinking is the caller's job. */
export function Lamp({ colour = 'amber', on, size, class: cls }: LampProps) {
  return (
    <span
      class={cls ? `lamp ${cls}` : 'lamp'}
      data-c={colour}
      data-on={on ? '1' : '0'}
      data-size={size}
      aria-hidden="true"
    />
  );
}
