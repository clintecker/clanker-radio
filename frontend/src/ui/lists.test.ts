import { beforeEach, describe, expect, it } from 'vitest';
import type { AppState } from '../lib/store';
import { parsePayload } from '../lib/payload';
import { renderHistory, renderQueue, renderStats } from './lists';

function state(partial: Record<string, unknown>): AppState {
  return {
    connection: 'live',
    receivedAt: Date.now(),
    clockOffsetMs: 0,
    data: parsePayload({ system_status: 'online', current: null, ...partial }),
  };
}

beforeEach(() => {
  document.body.innerHTML =
    '<div id="next-track"></div><div id="history-list"></div><span id="listeners"></span><span id="bitrate"></span><span id="samplerate"></span><span id="uptime"></span>';
});

describe('renderQueue', () => {
  it('shows a queued break first and the song after it', () => {
    renderQueue(
      state({
        breaks_queue: [{ asset_id: 'b', title: 'Station ID 0x1', source: 'bumper', duration_sec: 5 }],
        music_queue: [{ asset_id: 'm', title: 'Song', artist: 'A', source: 'music', duration_sec: 200 }],
      }),
    );
    const titles = [...document.querySelectorAll('#next-track .track-title')].map((n) => n.textContent);
    expect(titles).toEqual(['Station ID 0x1', '↳ then Song']);
    expect(document.querySelector('#next-track .track-bumper')).not.toBeNull();
  });

  it('renders feed text literally, never as markup', () => {
    renderQueue(
      state({
        music_queue: [
          { asset_id: 'm', title: '<img src=x onerror=alert(1)> & "Friends"', artist: '<b>bold</b>', source: 'music' },
        ],
      }),
    );
    expect(document.querySelector('#next-track img')).toBeNull();
    expect(document.querySelector('#next-track b')).toBeNull();
    expect(document.querySelector('#next-track .track-title')?.textContent).toBe(
      '<img src=x onerror=alert(1)> & "Friends"',
    );
  });

  it('explains an empty queue', () => {
    renderQueue(state({}));
    expect(document.querySelector('#next-track')?.textContent).toMatch(/Queue empty/);
  });
});

describe('renderHistory', () => {
  it('shows relative times and colours breaks and IDs', () => {
    const now = new Date('2026-09-22T12:00:00Z');
    renderHistory(
      state({
        history: [
          { asset_id: 'a', title: 'News', source: 'break', played_at: '2026-09-22T11:55:00Z' },
          { asset_id: 'b', title: 'Song', source: 'music', played_at: '2026-09-22T10:00:00Z' },
        ],
      }),
      now,
    );
    const rows = document.querySelectorAll('#history-list .track');
    expect(rows).toHaveLength(2);
    expect(rows[0]?.className).toContain('track-break');
    expect(rows[0]?.querySelector('.track-time')?.textContent).toBe('5m ago');
    expect(rows[1]?.querySelector('.track-time')?.textContent).toBe('2h ago');
  });
});

describe('renderStats', () => {
  it('picks the source matching the selected bitrate and falls back to the first', () => {
    const s = state({
      stream: {
        source: [
          { bitrate: 192, listeners: 3, samplerate: 48000 },
          { bitrate: 128, listeners: 7, samplerate: 44100 },
        ],
      },
    });
    renderStats(s, 128);
    expect(document.getElementById('listeners')?.textContent).toBe('7');
    expect(document.getElementById('samplerate')?.textContent).toBe('44.1 kHz');
    renderStats(s, 64);
    expect(document.getElementById('listeners')?.textContent).toBe('3');
  });

  it('dashes out when there is no stream info', () => {
    renderStats(state({}), 128);
    expect(document.getElementById('listeners')?.textContent).toBe('—');
    expect(document.getElementById('uptime')?.textContent).toBe('—');
  });
});
