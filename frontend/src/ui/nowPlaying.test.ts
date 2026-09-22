import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { parsePayload } from '../lib/payload';
import { Store } from '../lib/store';
import { NowPlayingView } from './nowPlaying';

const DOM = `
<section id="now-playing"><span id="np-kind"></span><div id="current-title"></div><div id="current-artist"></div>
<div id="current-meta"></div><div id="progress" hidden><div id="progress-fill"></div>
<span id="current-time"></span><span id="total-time"></span></div></section>`;

describe('NowPlayingView', () => {
  let store: Store;
  let view: NowPlayingView;
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-22T12:01:00Z'));
    document.body.innerHTML = DOM;
    store = new Store();
    view = new NowPlayingView(store);
  });
  afterEach(() => vi.useRealTimers());

  const push = (current: unknown) => {
    store.update({ data: parsePayload({ system_status: 'online', current }), receivedAt: Date.now() });
    return view.render(store.get());
  };

  it('computes elapsed time from played_at on the server clock', () => {
    push({ asset_id: 'a', title: 'T', duration_sec: 180, played_at: '2026-09-22T12:00:00Z', source: 'music' });
    expect(document.getElementById('current-time')?.textContent).toBe('1:00');
    expect(document.getElementById('progress-fill')?.style.width).toBe('33.33%');
    store.update({ clockOffsetMs: -30_000 }); // server is 30s behind us
    view.tick();
    expect(document.getElementById('current-time')?.textContent).toBe('0:30');
  });

  it('reports a change only when the play instance changes', () => {
    expect(push({ asset_id: 'a', title: 'T', played_at: '2026-09-22T12:00:00Z', source: 'music' })).toBe(true);
    expect(push({ asset_id: 'a', title: 'T', played_at: '2026-09-22T12:00:00Z', source: 'music' })).toBe(false);
    expect(push({ asset_id: 'a', title: 'T', played_at: '2026-09-22T12:00:30Z', source: 'music' })).toBe(true);
  });

  it('labels breaks and station IDs and clamps at the end', () => {
    push({ asset_id: 'n', title: 'Bulletin', duration_sec: 60, played_at: '2026-09-22T11:58:00Z', source: 'break' });
    expect(document.getElementById('np-kind')?.textContent).toBe('NEWS BULLETIN');
    expect(document.getElementById('current-time')?.textContent).toBe('1:00');
    expect(document.getElementById('now-playing')?.classList.contains('is-overrun')).toBe(true);
    expect(view.remainingSec()).toBeLessThan(0);
  });

  it('shows NO SIGNAL / SIGNAL LOST when nothing is playing', () => {
    push(null);
    expect(document.getElementById('current-title')?.textContent).toBe('NO SIGNAL');
    expect(document.getElementById('progress')!.hidden).toBe(true);
    store.update({ connection: 'stale' });
    view.render(store.get());
    expect(document.getElementById('current-title')?.textContent).toBe('SIGNAL LOST');
  });
});
