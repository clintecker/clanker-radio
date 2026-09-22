import { useEffect, useRef, useState } from 'preact/hooks';
import { fetchArchive, type ArchiveIndex, type Bulletin } from '../../lib/archive';
import { Lamp } from '../primitives/Lamp';
import { Legend } from '../primitives/Legend';
import { Panel } from '../primitives/Panel';

type Load = { kind: 'loading' } | { kind: 'error'; message: string } | { kind: 'ready'; index: ArchiveIndex };

/** Shared by the live module and the archive page. Index timestamps are station wall clock. */
export function useArchive(): Load {
  const [state, setState] = useState<Load>({ kind: 'loading' });
  useEffect(() => {
    const ctl = new AbortController();
    fetchArchive(ctl.signal)
      .then((index) => setState({ kind: 'ready', index }))
      .catch((err: unknown) => {
        if (!ctl.signal.aborted) setState({ kind: 'error', message: err instanceof Error ? err.message : String(err) });
      });
    return () => ctl.abort();
  }, []);
  return state;
}

const hhmm = (ts: string) => /T(\d{2}:\d{2})/.exec(ts)?.[1] ?? '--:--';
const day = (ts: string) => {
  const m = /^\d{4}-(\d{2})-(\d{2})/.exec(ts);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return m ? `${months[Number(m[1]) - 1] ?? ''} ${Number(m[2])}` : '';
};

/** One reel: time stamp, label, size; PLAY swaps the key for an inline player. */
export function BulletinRow({ b, index }: { b: Bulletin; index: number }) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const time = hhmm(b.timestamp);
  useEffect(() => {
    if (!open) return;
    audio.current?.focus();
    audio.current?.play().catch(() => undefined);
  }, [open]);
  return (
    <li class="tape">
      <span class="ts num">{time}</span>
      <p class="hl">
        News bulletin · {day(b.timestamp)}
        <small class="num">
          {index === 0 ? 'latest' : `${index} back`} · {(b.size_bytes / 1_048_576).toFixed(2)} MB
        </small>
      </p>
      {!open && (
        <button class="key" type="button" aria-label={`Play the ${time} bulletin`} onClick={() => setOpen(true)}>
          <Lamp colour="magenta" on={false} size="sm" />
          <span>Play</span>
        </button>
      )}
      {open && (
        <audio
          ref={audio}
          controls
          preload="none"
          src={b.url}
          aria-label={`${time} bulletin`}
          onError={() => setFailed(true)}
        />
      )}
      {failed && <p class="err">Reel missing. The {time} bulletin is not in the archive.</p>}
    </li>
  );
}

export function BulletinList({ load, limit }: { load: Load; limit?: number }) {
  const [more, setMore] = useState(false);
  if (load.kind === 'loading') return <p class="empty">Rewinding the reels…</p>;
  if (load.kind === 'error')
    return (
      <p class="empty err-line" role="alert">
        Archive offline ({load.message}). The live stream is unaffected.
      </p>
    );
  const all = load.index.breaks;
  if (!all.length) return <p class="empty">No bulletins in the last 24 hours.</p>;
  const head = limit ? all.slice(0, limit) : all;
  const rest = limit ? all.slice(limit) : [];
  return (
    <>
      <ul class="list tapes">
        {head.map((b, i) => (
          <BulletinRow key={b.url} b={b} index={i} />
        ))}
      </ul>
      {rest.length > 0 && (
        <>
          <ul class="list tapes" id="tapes-more" hidden={!more}>
            {rest.map((b, i) => (
              <BulletinRow key={b.url} b={b} index={i + head.length} />
            ))}
          </ul>
          <button
            class="key more"
            type="button"
            aria-expanded={more}
            aria-controls="tapes-more"
            onClick={() => setMore(!more)}
          >
            {more ? 'Archive ▾ hide' : `Archive ▸ ${rest.length} more`}
          </button>
        </>
      )}
    </>
  );
}

/** Compact bulletin module for the live page: the latest three, the rest of the day on demand. */
export function Bulletins() {
  const load = useArchive();
  return (
    <Panel name="arch" aria-labelledby="l-arch">
      <Legend en="Bulletins" zh="新闻" id="Berita" ru="Новости" htmlId="l-arch" note="on the hour" />
      <div class="window fill">
        <BulletinList load={load} limit={3} />
      </div>
    </Panel>
  );
}
