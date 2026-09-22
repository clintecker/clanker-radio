import './styles/main.css';
import { station } from './lib/config';
import { Player } from './lib/player';
import { FeedConnection } from './lib/sse';
import { Store } from './lib/store';
import { mountControls } from './ui/controls';
import { Crossfade } from './ui/crossfade';
import { byId } from './ui/dom';
import { renderHistory, renderQueue, renderStats } from './ui/lists';
import { NowPlayingView } from './ui/nowPlaying';
import { SignalDisplay } from './ui/signal';
import { renderStatus } from './ui/status';

const store = new Store();
const player = new Player(byId<HTMLAudioElement>('radio-stream'));
const nowPlaying = new NowPlayingView(store);
const crossfade = new Crossfade(store, nowPlaying);

document.title = `${station.name} // ${station.tagline}`;
mountControls(player);
new SignalDisplay(byId<HTMLCanvasElement>('signal'), player);

const errorBox = byId('player-error');
player.subscribe((snap) => {
  errorBox.hidden = snap.state !== 'error';
  errorBox.textContent = snap.state === 'error' ? 'Stream would not start. Check your connection and press RETRY.' : '';
  renderStats(store.get(), snap.stream.bitrate);
});

// Feed → screen. Everything below reads from the store, never from the wire directly.
store.subscribe((state, prev) => {
  renderStatus(state);
  if (state.data !== prev.data) {
    const changed = nowPlaying.render(state);
    if (changed && prev.data) crossfade.onTrackChanged();
    renderQueue(state);
    renderHistory(state);
    renderStats(state, player.snapshot().stream.bitrate);
  } else if (state.connection !== prev.connection && (state.connection === 'stale' || prev.connection === 'stale')) {
    nowPlaying.render(state);
  }
});

// Local clock: progress, crossfade window, relative timestamps. 4 Hz is plenty.
let lastHistoryRefresh = 0;
window.setInterval(() => {
  nowPlaying.tick();
  crossfade.tick();
  renderStatus(store.get());
  const now = Date.now();
  if (now - lastHistoryRefresh > 30_000) {
    lastHistoryRefresh = now;
    renderHistory(store.get());
  }
}, 250);

new FeedConnection(station.sseUrl, store).start();

byId('build-stamp').textContent = `BUILD ${__BUILD_STAMP__}`;

// Last line of defence: a runtime error in the page script should not leave a
// half-rendered screen with a LIVE badge on it.
window.addEventListener('error', (ev) => {
  console.error('Unhandled page error', ev.error ?? ev.message);
  byId('status-text').textContent = 'PAGE ERROR';
});
window.addEventListener('unhandledrejection', (ev) => console.error('Unhandled rejection', ev.reason));

// Media Session: lock-screen / hardware keys show the station and current track.
if ('mediaSession' in navigator) {
  navigator.mediaSession.setActionHandler('play', () => void player.play());
  navigator.mediaSession.setActionHandler('pause', () => player.stop());
  navigator.mediaSession.setActionHandler('stop', () => player.stop());
  store.subscribe((state) => {
    const t = state.data?.current;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t?.title || station.name,
      artist: t?.artist || '',
      album: station.name,
    });
  });
}
