import { describe, expect, it } from 'vitest';
import { PayloadError, parsePayload } from './payload';

const good = {
  updated_at: '2026-09-22T15:38:49.423063+00:00',
  system_status: 'online',
  crossfade: { music_sec: 4, breaks_sec: 0 },
  stream: {
    source: [
      {
        listenurl: '/radio',
        bitrate: 192,
        listeners: 1,
        listener_peak: 3,
        samplerate: 48000,
        channels: 2,
        stream_start_iso8601: '2026-09-19T04:57:53+0000',
      },
    ],
  },
  current: {
    asset_id: 'a',
    title: 'T',
    artist: 'A',
    album: 'Unknown Album',
    duration_sec: 211.6,
    played_at: '2026-09-22T15:38:49+00:00',
    source: 'music',
    kind: 'music',
  },
  breaks_queue: [],
  music_queue: [{ asset_id: 'b', title: 'Next', artist: 'A', album: null, source: 'music', duration_sec: 199 }],
  history: [{ asset_id: 'c', title: 'Prev', artist: 'A', played_at: '2026-09-22T15:30:00+00:00', source: 'bumper' }],
};

describe('parsePayload', () => {
  it('passes a well-formed payload through', () => {
    const p = parsePayload(good);
    expect(p.current?.title).toBe('T');
    expect(p.music_queue).toHaveLength(1);
    expect(p.history[0]?.source).toBe('bumper');
    expect('source' in p.stream && p.stream.source?.[0]?.bitrate).toBe(192);
  });

  it('rejects things that are not a payload at all', () => {
    expect(() => parsePayload(null)).toThrow(PayloadError);
    expect(() => parsePayload('<html>502</html>')).toThrow(PayloadError);
    expect(() => parsePayload({ foo: 1 })).toThrow(PayloadError);
  });

  it('degrades malformed fields instead of failing', () => {
    const p = parsePayload({
      system_status: 'online',
      current: { asset_id: 'x', title: 'Odd', duration_sec: 'NaN?' },
      music_queue: [null, 'junk', { title: 'ok' }],
      history: 'not a list',
      crossfade: 'nope',
      stream: { source: [{ bitrate: 'bad' }, { bitrate: 128 }] },
    });
    expect(p.current?.duration_sec).toBeNull();
    expect(p.music_queue.map((t) => t.title)).toEqual(['ok']);
    expect(p.history).toEqual([]);
    expect(p.crossfade).toEqual({ music_sec: 0, breaks_sec: 0 });
    expect('source' in p.stream && p.stream.source?.length).toBe(1);
  });

  it('treats a null current track as off-air, not an error', () => {
    expect(parsePayload({ system_status: 'online', current: null }).current).toBeNull();
  });

  it('keeps on_air_at and server_time when present', () => {
    const p = parsePayload({
      ...good,
      server_time: '2026-09-22T15:38:50.000000+00:00',
      current: { ...good.current, on_air_at: '2026-09-22T15:38:49.100000+00:00' },
    });
    expect(p.server_time).toBe('2026-09-22T15:38:50.000000+00:00');
    expect(p.current?.on_air_at).toBe('2026-09-22T15:38:49.100000+00:00');
  });
});
