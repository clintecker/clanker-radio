import type { ComponentChildren } from 'preact';
import { useEffect } from 'preact/hooks';
import { current } from '../../components/modules/console-state';
import { StatusStrip } from '../../components/modules/StatusStrip';
import { Ear } from '../../components/primitives/Ear';
import { station } from '../../lib/config';
import { player, startFeed } from '../../state';

/** The rack: ears, brand + status rail, and whatever page is mounted in it. Owns feed start and Media Session. */
export function ConsoleShell({ children }: { children: ComponentChildren }) {
  useEffect(() => {
    startFeed();
    const p = player;
    if (!('mediaSession' in navigator) || !p) return;
    navigator.mediaSession.setActionHandler('play', () => void p.play());
    navigator.mediaSession.setActionHandler('pause', () => p.stop());
    navigator.mediaSession.setActionHandler('stop', () => p.stop());
  }, []);

  const t = current.value;
  useEffect(() => {
    document.title = t?.title ? `${t.title} · ${station.name}` : `${station.name} // ${station.tagline}`;
    if ('mediaSession' in navigator)
      navigator.mediaSession.metadata = new MediaMetadata({
        title: t?.title || station.name,
        artist: t?.artist || '',
        album: station.name,
      });
  }, [t?.title, t?.artist]);

  return (
    <div class="rack console">
      <Ear side="l" />
      <Ear side="r" />
      <div class="rack-inner">
        <StatusStrip />
        {children}
        <p class="build engr-2">BUILD {__BUILD_STAMP__}</p>
      </div>
    </div>
  );
}
