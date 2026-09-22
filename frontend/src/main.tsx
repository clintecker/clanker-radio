import { render } from 'preact';
import { station } from './lib/config';
import { resolveUiMode } from './ui-mode';

document.title = `${station.name} // ${station.tagline}`;

// Last line of defence: a runtime error must not leave a half-rendered page claiming LIVE.
window.addEventListener('error', (ev) => {
  console.error('Unhandled page error', ev.error ?? ev.message);
  const badge = document.getElementById('status-text');
  if (badge) badge.textContent = 'PAGE ERROR';
});
window.addEventListener('unhandledrejection', (ev) => console.error('Unhandled rejection', ev.reason));

const root = document.getElementById('app');
if (!root) throw new Error('missing #app');
const mountAt = root;

// Each face ships its own stylesheet, so the classic page never downloads the console's and vice versa.
const kit = import.meta.env.DEV && location.pathname === '/__kit';
if (kit || resolveUiMode(location.search) === 'console') {
  void import('./console-app').then((m) => m.mountConsole(mountAt));
} else {
  void import('./app').then(({ App }) => render(<App />, mountAt));
}
