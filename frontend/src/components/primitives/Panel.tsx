import type { ComponentChildren, HTMLAttributes } from 'preact';
import { Screw } from './Screw';

export interface PanelProps extends Omit<HTMLAttributes<HTMLElement>, 'class'> {
  /** Grid area / module name; also seeds the screw turns. */
  name: string;
  class?: string;
  children?: ComponentChildren;
}

/** A raised sub-plate screwed to the faceplate. */
export function Panel({ name, class: cls, children, ...rest }: PanelProps) {
  return (
    <section class={`module ${name}${cls ? ` ${cls}` : ''}`} {...rest}>
      {children}
      {(['tl', 'tr', 'bl', 'br'] as const).map((p) => (
        <Screw key={p} seed={name + p} pos={p} />
      ))}
    </section>
  );
}
