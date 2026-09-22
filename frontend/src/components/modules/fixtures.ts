import { parsePayload } from '../../lib/payload';
import type { NowPlayingPayload } from '../../lib/types';

export const NOW = Date.parse('2026-09-22T17:10:49Z');

export const LONG =
  'FIFTY-NINE SECONDS OF SUMMER (Yamamoto / Detroit Cover) — Extended Rooftop Antenna Mix For The Curfew Hours Part II';
export const CYRILLIC = 'ЛИТАНИЯ АПТАЙМА / Λιτανεία Uptime';
export const CJK = '夜间巡逻 · 無人機';
export const TAGGED = 'Previous <b>Song</b> <img src=x onerror=alert(1)>';

export function fixture(over: Record<string, unknown> = {}): NowPlayingPayload {
  return parsePayload({
    updated_at: '2026-09-22T17:09:49Z',
    system_status: 'online',
    crossfade: { music_sec: 4, breaks_sec: 0 },
    stream: {
      source: [
        {
          listenurl: '/radio',
          listeners: 2,
          listener_peak: 4,
          bitrate: 192,
          samplerate: 48000,
          channels: 2,
          stream_start_iso8601: '2026-09-19T04:57:53+0000',
        },
        { listenurl: '/radio-128', listeners: 5, listener_peak: 9, bitrate: 128, samplerate: 44100, channels: 2 },
        { listenurl: '/radio-96', listeners: 0, listener_peak: 1, bitrate: 96, samplerate: 44100, channels: 2 },
        {
          listenurl: '/radio-fallback',
          listeners: 40,
          listener_peak: 99,
          bitrate: 192,
          samplerate: 48000,
          channels: 2,
        },
      ],
    },
    current: {
      asset_id: 'cur',
      title: LONG,
      artist: 'Clint Ecker',
      album: 'Unknown Album',
      duration_sec: 213.6,
      played_at: '2026-09-22T17:09:49Z',
      source: 'music',
      kind: 'music',
    },
    breaks_queue: [{ asset_id: 'id1', title: 'Station ID 0xE2E', artist: 'LBR', source: 'bumper', duration_sec: 21 }],
    music_queue: [
      { asset_id: 'm1', title: CJK, artist: '匿名', source: 'music', duration_sec: 139 },
      { asset_id: 'm2', title: TAGGED, artist: 'E2E', source: 'music', duration_sec: 151 },
    ],
    history: [
      {
        asset_id: 'h1',
        title: CYRILLIC,
        artist: 'Clint Ecker',
        source: 'music',
        duration_sec: 277,
        played_at: '2026-09-22T17:03:13Z',
      },
      {
        asset_id: 'h2',
        title: 'Bulletin 16:00',
        artist: 'Newsroom',
        source: 'break',
        duration_sec: 94,
        played_at: '2026-09-22T16:00:00Z',
      },
    ],
    ...over,
  });
}
