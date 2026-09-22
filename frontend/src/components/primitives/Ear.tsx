import { Screw } from './Screw';

/** Rack ear: two slotted screws, a pull handle, a scraped hazard stripe (CSS) and a bottom screw. */
export function Ear({ side }: { side: 'l' | 'r' }) {
  return (
    <div class={`ear ${side}`} aria-hidden="true">
      {[22, 250].map((top) => (
        <span key={top} class="slot" style={{ top: `${top}px` }}>
          <Screw seed={`${side}${top}`} />
        </span>
      ))}
      <span class="handle" />
      <span class="slot" style={{ bottom: '22px' }}>
        <Screw seed={`${side}b`} />
      </span>
    </div>
  );
}
