import { useEffect, useState } from 'preact/hooks';
import { formatClock } from '../lib/format';
import { trackKind, type Track } from '../lib/types';
import { app, programNow } from '../state';
import { Signal } from './Signal';
import { StatusBadge } from './StatusBadge';

const KIND_LABEL: Record<string, string> = { music: 'NOW TRANSMITTING', break: 'NEWS BULLETIN', bumper: 'STATION ID' };
const TITLE_COLOR: Record<string, string> = {
  music: 'text-phosphor-bright glow',
  break: 'text-amber glow-amber',
  bumper: 'text-cyan glow-cyan',
};

export function playKey(t: Track | null): string | null {
  return t ? `${t.asset_id}|${t.played_at ?? ''}` : null;
}

/** Elapsed seconds on the server clock, or null when the start time is unknown. */
export function elapsedSec(t: Track | null, nowMs: number): number | null {
  if (!t?.played_at) return null;
  const start = Date.parse(t.played_at);
  return Number.isNaN(start) ? null : Math.max(0, (nowMs - start) / 1000);
}

export function remainingSec(t: Track | null, nowMs: number): number | null {
  const e = elapsedSec(t, nowMs);
  if (e === null || !t?.duration_sec) return null;
  return t.duration_sec - e;
}

/** The queued track that will play next, and the crossfade length that applies. */
export function upNext(): { next: Track | null; fadeSec: number } {
  const d = app.value.data;
  if (!d) return { next: null, fadeSec: 0 };
  const next = d.breaks_queue[0] ?? d.music_queue[0] ?? null;
  return { next, fadeSec: d.breaks_queue.length ? d.crossfade.breaks_sec : d.crossfade.music_sec };
}

function Card({ track, ghost = false, animate = false }: { track: Track; ghost?: boolean; animate?: boolean }) {
  const kind = trackKind(track);
  const duration = track.duration_sec ?? 0;
  const e = elapsedSec(track, programNow.value);
  const shown = e === null ? null : duration > 0 ? Math.min(e, duration) : e;
  const pct = shown !== null && duration > 0 ? (shown / duration) * 100 : 0;
  const overrun = e !== null && duration > 0 && e > duration + 2;
  return (
    <section
      class={
        ghost
          ? 'absolute inset-x-0 top-0 pointer-events-none animate-glitch-out motion-safe-only z-10'
          : `relative ${animate ? 'animate-fade-in motion-safe-only' : ''}`
      }
      data-kind={kind}
      aria-hidden={ghost}
    >
      <div class="flex items-center gap-3.5 text-[0.6rem] tracking-eyebrow text-phosphor-dim mb-2.5">
        <span>{KIND_LABEL[kind] ?? 'NOW TRANSMITTING'}</span>
        {!ghost && <StatusBadge />}
      </div>
      <h2
        class={`text-[2rem] max-sm:text-2xl leading-tight mb-2 font-normal [overflow-wrap:anywhere] ${TITLE_COLOR[kind] ?? TITLE_COLOR.music}`}
      >
        {track.title || 'Unknown Track'}
      </h2>
      <div class="text-xl max-sm:text-base mb-3 [overflow-wrap:anywhere]">{track.artist || 'Unknown Artist'}</div>
      <div class="text-xs text-phosphor-dim min-h-[1.2em] flex gap-2">
        {track.album && track.album !== 'Unknown Album' && <span>{track.album}</span>}
        {kind !== 'music' && (
          <span class="border border-current px-1.5 text-[0.6rem] tracking-[0.15em]">
            {kind === 'break' ? 'NEWS' : 'ID'}
          </span>
        )}
      </div>
      {e !== null && (
        <div class="mt-5">
          <div class="h-0.5 bg-phosphor/15 overflow-hidden">
            <div
              class={`h-full transition-[width] duration-250 ease-linear ${overrun ? 'bg-phosphor-dim' : 'bg-phosphor shadow-[0_0_8px_var(--color-phosphor)]'}`}
              style={{ width: `${pct.toFixed(2)}%` }}
            />
          </div>
          <div class="text-[0.65rem] text-phosphor-dim mt-1 tabular-nums">
            <span data-testid="elapsed">{formatClock(shown)}</span> / {formatClock(duration)}
            {overrun && <span> · awaiting next</span>}
          </div>
        </div>
      )}
      {!ghost && <Signal />}
    </section>
  );
}

/**
 * Hero. Content only ever reflects what the server says is playing. The crossfade
 * animates around it: inside the window an INCOMING strip names the queued track
 * and, once the feed confirms the change, the previous card glitches out as a ghost.
 */
export function NowPlaying() {
  const { data, connection } = app.value;
  const current = data?.current ?? null;
  const key = playKey(current);
  const [ghost, setGhost] = useState<{ track: Track; key: string } | null>(null);
  const [lastKey, setLastKey] = useState<string | null>(null);
  const [lastTrack, setLastTrack] = useState<Track | null>(null);
  const [changes, setChanges] = useState(0);

  useEffect(() => {
    if (key === lastKey) return;
    if (lastTrack && current) {
      setGhost({ track: lastTrack, key: lastKey ?? '' });
      setChanges((n) => n + 1);
    }
    setLastKey(key);
    setLastTrack(current);
  }, [key]);

  useEffect(() => {
    if (!ghost) return;
    const fade = Math.max(1.5, upNext().fadeSec || 4);
    const t = window.setTimeout(() => setGhost(null), fade * 1000 + 200);
    return () => window.clearTimeout(t);
  }, [ghost]);

  if (!current) {
    return (
      <section class="relative mb-10">
        <div class="flex items-center gap-3.5 text-[0.6rem] tracking-eyebrow text-phosphor-dim mb-2.5">
          <span>NOW TRANSMITTING</span>
          <StatusBadge />
        </div>
        <h2 class="text-[2rem] text-phosphor-bright glow">
          {connection === 'stale' ? 'SIGNAL LOST' : connection === 'connecting' ? 'Tuning…' : 'NO SIGNAL'}
        </h2>
        <Signal />
      </section>
    );
  }

  const { next, fadeSec } = upNext();
  const remaining = trackKind(current) === 'music' ? remainingSec(current, programNow.value) : null;
  const incoming =
    next && fadeSec > 0 && remaining !== null && remaining <= fadeSec + 1 && remaining > -5 ? next : null;

  return (
    <div class="relative mb-10" aria-live="polite">
      {ghost && <Card key={`ghost-${ghost.key}`} track={ghost.track} ghost />}
      {/* Fade in only when replacing a previous track; first paint is instant. */}
      <Card key={key ?? 'none'} track={current} animate={changes > 0} />
      {incoming && (
        <div
          class="grid grid-cols-[auto_1fr_auto] max-sm:grid-cols-1 gap-3 max-sm:gap-0.5 items-baseline mt-3.5 pt-2.5 border-t border-dashed border-phosphor-faint text-[0.8rem] animate-rise motion-safe-only"
          data-testid="incoming"
        >
          <span class="text-[0.6rem] tracking-[0.2em] text-cyan whitespace-nowrap">
            {trackKind(incoming) === 'music'
              ? 'INCOMING'
              : trackKind(incoming) === 'break'
                ? 'INCOMING · NEWS'
                : 'INCOMING · ID'}
          </span>
          <span class="truncate">{incoming.title || 'Unknown'}</span>
          <span class="text-phosphor-dim text-[0.7rem] whitespace-nowrap">{incoming.artist ?? ''}</span>
        </div>
      )}
    </div>
  );
}
