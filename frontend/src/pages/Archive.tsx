import { useEffect, useState } from 'preact/hooks';
import { fetchArchive, formatBulletinTime, type ArchiveIndex } from '../lib/archive';

type State = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; index: ArchiveIndex };

/** The last day of news bulletins, playable in place. */
export function Archive() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [playing, setPlaying] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    fetchArchive(ctl.signal)
      .then((index) => setState({ kind: 'ready', index }))
      .catch((err: unknown) => {
        if (ctl.signal.aborted) return;
        setState({ kind: 'error', message: err instanceof Error ? err.message : String(err) });
      });
    return () => ctl.abort();
  }, []);

  return (
    <section class="mb-10" aria-labelledby="archive-heading">
      <div class="eyebrow" id="archive-heading">
        BULLETIN ARCHIVE · LAST 24 HOURS
      </div>
      {state.kind === 'loading' && <p class="text-[0.8rem] text-phosphor-dim py-2.5">Retrieving transmissions…</p>}
      {state.kind === 'error' && (
        <p class="text-[0.8rem] text-alarm py-2.5" role="alert">
          Archive unavailable ({state.message}). The live stream is unaffected.
        </p>
      )}
      {state.kind === 'ready' && state.index.breaks.length === 0 && (
        <p class="text-[0.8rem] text-phosphor-dim py-2.5">No bulletins in the last 24 hours.</p>
      )}
      {state.kind === 'ready' &&
        state.index.breaks.map((b) => (
          <article key={b.url} class="py-2.5 border-b border-phosphor/5 last:border-b-0 text-[0.8rem]">
            <div class="flex justify-between items-baseline gap-4">
              <div class="min-w-0">
                <div class="text-amber italic truncate">News bulletin · {formatBulletinTime(b.timestamp)}</div>
                <div class="text-phosphor-dim text-[0.7rem] tabular-nums">
                  {(b.size_bytes / 1_048_576).toFixed(1)} MB
                </div>
              </div>
              <div class="flex gap-3 whitespace-nowrap text-[0.65rem] tracking-[0.15em]">
                <button
                  type="button"
                  class="text-phosphor hover:text-phosphor-bright cursor-pointer"
                  onClick={() => setPlaying(playing === b.url ? null : b.url)}
                  aria-expanded={playing === b.url}
                >
                  {playing === b.url ? 'CLOSE' : 'PLAY'}
                </button>
                <a class="text-phosphor-dim hover:text-phosphor no-underline" href={b.url} download>
                  SAVE
                </a>
              </div>
            </div>
            {playing === b.url && <audio class="mt-2 w-full h-8" controls autoplay src={b.url} preload="none" />}
          </article>
        ))}
    </section>
  );
}
