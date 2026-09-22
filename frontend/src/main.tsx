import { render } from 'preact';
import './styles/app.css';
import { App } from './app';
import { station } from './lib/config';

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
render(<App />, root);
