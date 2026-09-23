import { render, screen, waitFor } from '@testing-library/preact';
import { beforeEach, describe, expect, it } from 'vitest';
import { parsePayload } from '../lib/payload';
import { app, now } from '../state';
import { NowPlaying, elapsedSec, remainingSec } from './NowPlaying';

function feed(
  current: unknown,
  extra: Record<string, unknown> = {},
  connection: 'live' | 'stale' | 'connecting' = 'live',
) {
  app.value = {
    connection,
    receivedAt: Date.now(),
    clockOffsetMs: 0,
    listenerDelayMs: 0,
    data: parsePayload({ system_status: 'online', current, crossfade: { music_sec: 4, breaks_sec: 0 }, ...extra }),
  };
}

beforeEach(() => {
  now.value = Date.parse('2026-09-22T12:01:00Z');
});

describe('NowPlaying', () => {
  it('computes elapsed time from played_at on the server clock', async () => {
    feed({ asset_id: 'a', title: 'T', duration_sec: 180, played_at: '2026-09-22T12:00:00Z', source: 'music' });
    render(<NowPlaying />);
    expect(screen.getByTestId('elapsed')).toHaveTextContent('1:00');
    app.value = { ...app.value, clockOffsetMs: -30_000 }; // server is 30s behind us
    await waitFor(() => expect(screen.getByTestId('elapsed')).toHaveTextContent('0:30'));
  });

  it('labels bulletins and flags overrun past the end', () => {
    feed({ asset_id: 'n', title: 'Bulletin', duration_sec: 60, played_at: '2026-09-22T11:58:00Z', source: 'break' });
    render(<NowPlaying />);
    expect(screen.getByText('NEWS BULLETIN')).toBeInTheDocument();
    expect(screen.getByTestId('elapsed')).toHaveTextContent('1:00');
    expect(screen.getByText(/awaiting next/)).toBeInTheDocument();
  });

  it('announces the incoming track only inside the crossfade window, and only for music', () => {
    const next = [{ asset_id: 'b', title: 'Next Song', source: 'music', duration_sec: 100 }];
    feed(
      { asset_id: 'a', title: 'T', duration_sec: 180, played_at: '2026-09-22T12:00:00Z', source: 'music' },
      { music_queue: next },
    );
    const { rerender } = render(<NowPlaying />);
    expect(screen.queryByTestId('incoming')).toBeNull(); // 120s remaining
    now.value = Date.parse('2026-09-22T12:02:56Z'); // 4s remaining: inside fade (4s) + 1s
    rerender(<NowPlaying />);
    expect(screen.getByTestId('incoming')).toHaveTextContent('Next Song');
    feed(
      { asset_id: 'n', title: 'Bulletin', duration_sec: 60, played_at: '2026-09-22T12:02:00Z', source: 'break' },
      { music_queue: next },
    );
    rerender(<NowPlaying />);
    expect(screen.queryByTestId('incoming')).toBeNull();
  });

  it('shows NO SIGNAL / SIGNAL LOST when nothing is playing', () => {
    feed(null);
    const { rerender } = render(<NowPlaying />);
    expect(screen.getByText('NO SIGNAL')).toBeInTheDocument();
    feed(null, {}, 'stale');
    rerender(<NowPlaying />);
    expect(screen.getByText('SIGNAL LOST')).toBeInTheDocument();
  });
});

describe('time helpers', () => {
  it('handle unknown starts and durations', () => {
    expect(elapsedSec(null, 0)).toBeNull();
    expect(
      elapsedSec({ asset_id: 'a', title: 't', artist: null, album: null, duration_sec: 10, source: 'music' }, 0),
    ).toBeNull();
    expect(
      remainingSec(
        {
          asset_id: 'a',
          title: 't',
          artist: null,
          album: null,
          duration_sec: null,
          source: 'music',
          played_at: '2026-09-22T12:00:00Z',
        },
        Date.parse('2026-09-22T12:00:10Z'),
      ),
    ).toBeNull();
  });
});
