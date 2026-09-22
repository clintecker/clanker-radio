import type { ComponentChildren } from 'preact';

export interface TriProps {
  zh: string;
  id?: string;
  ru?: string;
}

/** Secondary legend in 中文 · Bahasa · Русский, as printed on grey-market parts. Decorative. */
export function Tri({ zh, id, ru }: TriProps) {
  return (
    <span class="tri" aria-hidden="true">
      <span class="zh" lang="zh">
        {zh}
      </span>
      {id && (
        <>
          {' '}
          <span lang="id">{id}</span>
        </>
      )}
      {ru && (
        <>
          {' · '}
          <span lang="ru">{ru}</span>
        </>
      )}
    </span>
  );
}

export interface LegendProps extends TriProps {
  en: string;
  htmlId?: string;
  note?: ComponentChildren;
  level?: 2 | 3;
}

/** Engraved module heading: English legend, trilingual sub-legend, optional right-hand note. */
export function Legend({ en, zh, id, ru, htmlId, note, level = 2 }: LegendProps) {
  const H = level === 2 ? 'h2' : 'h3';
  return (
    <H class="legend engr" id={htmlId}>
      <span>
        {en}
        <Tri zh={zh} id={id} ru={ru} />
      </span>
      {note != null && <span class="engr-2">{note}</span>}
    </H>
  );
}
