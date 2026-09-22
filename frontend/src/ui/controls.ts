import { streams } from '../lib/config';
import type { Player, PlayerSnapshot } from '../lib/player';
import { byId, el } from './dom';

const BUTTON_LABEL: Record<PlayerSnapshot['state'], string> = {
  idle: 'TUNE IN',
  loading: 'TUNING…',
  playing: 'TUNE OUT',
  error: 'RETRY',
};

/** Wires the transport controls to the Player and keeps them in sync with its state. */
export function mountControls(player: Player): void {
  const button = byId<HTMLButtonElement>('play-button');
  const volume = byId<HTMLInputElement>('volume');
  const volumeWrap = byId('volume-control');
  const quality = byId<HTMLSelectElement>('quality-selector');

  quality.replaceChildren(...streams.map((s) => el('option', { value: s.path }, s.label)));

  button.addEventListener('click', () => void player.toggle());
  volume.addEventListener('input', () => player.setVolume(Number(volume.value) / 100));
  quality.addEventListener('change', () => void player.setStream(quality.value));

  player.subscribe((snap) => {
    button.textContent = BUTTON_LABEL[snap.state];
    button.dataset.state = snap.state;
    button.setAttribute('aria-pressed', String(snap.state === 'playing' || snap.state === 'loading'));
    volume.value = String(Math.round(snap.volume * 100));
    volumeWrap.hidden = !snap.volumeSupported;
    quality.value = snap.stream.path;
  });
}
