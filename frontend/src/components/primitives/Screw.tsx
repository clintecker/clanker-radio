/** Cheap stable hash so a screw keeps its turn across renders (and screenshots). */
export function turnFor(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  return (h >>> 0) % 180;
}

export type ScrewPos = 'tl' | 'tr' | 'bl' | 'br';

export function Screw({ seed, pos }: { seed: string; pos?: ScrewPos }) {
  return <span class={pos ? `screw ${pos}` : 'screw'} style={{ '--r': `${turnFor(seed)}deg` }} aria-hidden="true" />;
}
