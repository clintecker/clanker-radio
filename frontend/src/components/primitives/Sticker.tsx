import type { ComponentChildren, CSSProperties } from 'preact';

export type StickerVariant = 'zhs' | 'idn' | 'cyr' | 'asset' | 'tape';

export interface StickerProps {
  variant: StickerVariant;
  style?: CSSProperties;
  /** Flow in layout instead of being absolutely pinned (for the kit page). */
  inline?: boolean;
  children: ComponentChildren;
}

/** Hand-applied marking: decorative, hidden from assistive tech. */
export function Sticker({ variant, style, inline, children }: StickerProps) {
  const cls = variant === 'tape' ? 'tape-strip' : `sticker ${variant}`;
  return (
    <span class={inline ? `${cls} static` : cls} style={style} aria-hidden="true">
      {children}
    </span>
  );
}
