import type { Store } from '../lib/store';
import { trackKind, type Track } from '../lib/types';
import { byId, el } from './dom';
import type { NowPlayingView } from './nowPlaying';

/**
 * Visual crossfade that mirrors Liquidsoap's audio crossfade.
 *
 * Two phases keep it honest:
 *  1. "incoming": inside the crossfade window we show a labelled strip with the
 *     queued track below the hero, and start the glitch-out on the old card.
 *  2. "swap": only when the SSE feed confirms a new current track do we clear
 *     the strip. If the server's next track differs from what we anticipated
 *     (a break got inserted late), nothing wrong was ever displayed as "now".
 */
export class Crossfade {
  private readonly container = byId('now-playing-container');
  private readonly card = byId('now-playing');
  private readonly incoming = byId('incoming');
  private anticipating: string | null = null;
  private ghost: HTMLElement | null = null;
  private ghostTimer: number | null = null;

  constructor(
    private readonly store: Store,
    private readonly view: NowPlayingView,
  ) {}

  /** Runs each tick. Decides whether we are inside the window before the next track. */
  tick(): void {
    const data = this.store.get().data;
    const current = data?.current;
    if (!data || !current || trackKind(current) !== 'music') {
      this.clearIncoming();
      return;
    }

    const next = data.breaks_queue[0] ?? data.music_queue[0];
    if (!next) {
      this.clearIncoming();
      return;
    }
    const fade = data.breaks_queue.length ? data.crossfade.breaks_sec : data.crossfade.music_sec;
    const remaining = this.view.remainingSec();
    if (remaining === null) {
      this.clearIncoming();
      return;
    }

    // One second early absorbs SSE latency; the ghost animation runs for the fade length.
    const inWindow = remaining <= fade + 1 && remaining > -5;
    if (inWindow && this.anticipating !== next.asset_id) this.showIncoming(next, Math.max(fade, 1.5));
    else if (!inWindow) this.clearIncoming();
  }

  /** The feed confirmed a new current track: finish the transition. */
  onTrackChanged(): void {
    this.clearIncoming();
    this.card.classList.remove('fade-in');
    // Reading offsetWidth forces a reflow so the animation restarts.
    this.card.style.setProperty('--reflow', String(this.card.offsetWidth));
    this.card.classList.add('fade-in');
  }

  private showIncoming(next: Track, seconds: number): void {
    this.anticipating = next.asset_id;
    const kind = trackKind(next);
    this.incoming.replaceChildren(
      el(
        'span',
        { class: 'incoming-label' },
        kind === 'music' ? 'INCOMING' : kind === 'break' ? 'INCOMING · NEWS' : 'INCOMING · ID',
      ),
      el('span', { class: 'incoming-title' }, next.title || 'Unknown'),
      el('span', { class: 'incoming-artist' }, next.artist || ''),
    );
    this.incoming.hidden = false;

    // Ghost: a frozen clone of the current card that glitches out over the fade.
    this.removeGhost();
    const ghost = this.card.cloneNode(true) as HTMLElement;
    ghost.removeAttribute('id');
    ghost.querySelectorAll('[id]').forEach((n) => n.removeAttribute('id'));
    ghost.classList.add('ghost');
    ghost.style.animationDuration = `${seconds}s`;
    ghost.setAttribute('aria-hidden', 'true');
    this.container.append(ghost);
    this.ghost = ghost;
    this.ghostTimer = window.setTimeout(() => this.removeGhost(), seconds * 1000 + 200);
  }

  private clearIncoming(): void {
    if (this.anticipating === null) return;
    this.anticipating = null;
    this.incoming.hidden = true;
    this.incoming.replaceChildren();
  }

  private removeGhost(): void {
    if (this.ghostTimer) window.clearTimeout(this.ghostTimer);
    this.ghost?.remove();
    this.ghost = null;
    this.ghostTimer = null;
  }
}
