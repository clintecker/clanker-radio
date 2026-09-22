import { formatClock, formatTimeAgo } from '../lib/format';
import { trackKind, type Track } from '../lib/types';
import { app, now } from '../state';

const TITLE: Record<string, string> = {
  music: 'text-phosphor',
  break: 'text-amber italic',
  bumper: 'text-cyan italic',
  unknown: 'text-phosphor',
};

export function TrackRow({
  track,
  trailing,
  muted = false,
  prefix,
  accent,
}: {
  track: Track;
  trailing: string;
  muted?: boolean;
  prefix?: string;
  accent?: string;
}) {
  const kind = trackKind(track);
  return (
    <div
      class={`flex justify-between items-baseline gap-4 py-2.5 border-b border-phosphor/5 last:border-b-0 text-[0.8rem] ${kind !== 'music' ? 'opacity-70' : ''} ${muted ? 'opacity-50 text-[0.75rem]' : ''}`}
      data-kind={kind}
    >
      <div class="flex-1 min-w-0">
        <div class={`truncate mb-0.5 ${accent && kind === 'music' ? accent : TITLE[kind]}`}>
          {prefix ? `${prefix} ` : ''}
          {track.title || 'Unknown'}
        </div>
        <div class="truncate text-phosphor-dim text-[0.7rem]">{track.artist || 'Unknown Artist'}</div>
      </div>
      <div class="text-phosphor-dim text-[0.65rem] whitespace-nowrap tabular-nums">{trailing}</div>
    </div>
  );
}

function Empty({ children }: { children: string }) {
  return <div class="py-2.5 text-[0.8rem] text-phosphor-dim">{children}</div>;
}

/** NEXT UP: a break (if queued) always plays before the next song, so show both. */
export function Queue() {
  const d = app.value.data;
  const nextBreak = d?.breaks_queue[0];
  const nextMusic = d?.music_queue[0];
  return (
    <section class="mb-10" aria-labelledby="next-heading">
      <div class="eyebrow" id="next-heading">
        NEXT UP
      </div>
      {nextBreak ? (
        <>
          <TrackRow track={nextBreak} trailing={formatClock(nextBreak.duration_sec)} />
          {nextMusic && (
            <TrackRow track={nextMusic} trailing={formatClock(nextMusic.duration_sec)} muted prefix="↳ then" />
          )}
        </>
      ) : nextMusic ? (
        <TrackRow track={nextMusic} trailing={formatClock(nextMusic.duration_sec)} accent="text-cyan" />
      ) : (
        <Empty>Queue empty · automation will pick the next track</Empty>
      )}
    </section>
  );
}

/** RECENT TRANSMISSIONS. Relative times re-render with the shared clock, so "3m ago" keeps moving between pushes. */
export function History() {
  const history = app.value.data?.history ?? [];
  const at = new Date(now.value);
  return (
    <section class="mb-10" aria-labelledby="history-heading">
      <div class="eyebrow" id="history-heading">
        RECENT TRANSMISSIONS
      </div>
      {history.length ? (
        history.map((t, i) => (
          <TrackRow
            key={`${t.asset_id}-${t.played_at ?? i}`}
            track={t}
            trailing={t.played_at ? formatTimeAgo(new Date(t.played_at), at) : ''}
          />
        ))
      ) : (
        <Empty>No transmissions logged yet</Empty>
      )}
    </section>
  );
}
