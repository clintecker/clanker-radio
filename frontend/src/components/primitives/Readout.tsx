import type { ComponentChildren, HTMLAttributes, Ref } from 'preact';
import type { TrackKind } from '../../lib/types';

export interface ReadoutProps extends Omit<HTMLAttributes<HTMLDivElement>, 'class' | 'ref'> {
  kind?: TrackKind;
  /** Scanline mask over the glass (VFD). */
  scan?: boolean;
  class?: string;
  innerRef?: Ref<HTMLDivElement>;
  children?: ComponentChildren;
}

/**
 * Recessed VFD glass. Children are rendered as Preact text/elements, never markup,
 * so feed strings containing tags stay literal.
 */
export function Readout({ kind, scan, class: cls, innerRef, children, ...rest }: ReadoutProps) {
  return (
    <div class={`window${scan ? ' scan' : ''}${cls ? ` ${cls}` : ''}`} data-kind={kind} ref={innerRef} {...rest}>
      {children}
    </div>
  );
}
