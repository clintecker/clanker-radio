import './styles/app.css';
import { LocationProvider, Route, Router, useLocation } from 'preact-iso';
import { useEffect } from 'preact/hooks';
import { station } from './lib/config';
import { Archive } from './pages/Archive';
import { Live } from './pages/Live';
import { app, player, startFeed } from './state';

function NavLink({ href, children }: { href: string; children: string }) {
  const { path } = useLocation();
  const active = path === href;
  return (
    <a
      href={href}
      class={`text-[0.65rem] tracking-[0.2em] no-underline pb-1 border-b ${active ? 'text-phosphor border-phosphor' : 'text-phosphor-dim border-transparent hover:text-phosphor'}`}
      aria-current={active ? 'page' : undefined}
    >
      {children}
    </a>
  );
}

function NotFound() {
  return (
    <section class="mb-10">
      <div class="eyebrow">404</div>
      <p class="text-[0.8rem]">
        No such frequency. <a href="/">Back to the live signal.</a>
      </p>
    </section>
  );
}

function Shell() {
  useEffect(() => {
    startFeed();
    // Media Session: lock-screen / hardware keys show the station and current track.
    const p = player;
    if (!('mediaSession' in navigator) || !p) return;
    navigator.mediaSession.setActionHandler('play', () => void p.play());
    navigator.mediaSession.setActionHandler('pause', () => p.stop());
    navigator.mediaSession.setActionHandler('stop', () => p.stop());
    return app.subscribe((s) => {
      const t = s.data?.current;
      navigator.mediaSession.metadata = new MediaMetadata({
        title: t?.title || station.name,
        artist: t?.artist || '',
        album: station.name,
      });
    });
  }, []);

  return (
    <div class="max-w-[900px] mx-auto px-4 py-5">
      <header class="mb-10 pb-4 border-b border-phosphor-dim flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-xl tracking-[0.3em] text-phosphor-bright font-normal mb-1">{station.name}</h1>
          <div class="text-[0.7rem] text-phosphor-dim tracking-[0.2em]">{station.tagline}</div>
        </div>
        <nav class="flex gap-5" aria-label="Sections">
          <NavLink href="/">LIVE</NavLink>
          <NavLink href="/archive">ARCHIVE</NavLink>
        </nav>
      </header>
      <main>
        <Router>
          <Route path="/" component={Live} />
          <Route path="/archive" component={Archive} />
          <Route default component={NotFound} />
        </Router>
      </main>
      <footer class="mt-12 pt-5 border-t border-phosphor-faint text-center text-[0.65rem] tracking-[0.15em]">
        <a href={station.playlistUrl} class="text-phosphor-dim no-underline hover:text-phosphor" download>
          DOWNLOAD M3U PLAYLIST
        </a>
        <div class="mt-2.5 text-[0.55rem] text-phosphor-dim opacity-60 tracking-[0.1em]">BUILD {__BUILD_STAMP__}</div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <LocationProvider>
      <Shell />
    </LocationProvider>
  );
}
