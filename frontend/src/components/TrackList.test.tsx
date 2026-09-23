import { render, screen, waitFor } from '@testing-library/preact';
import { beforeEach, describe, expect, it } from 'vitest';
import { parsePayload } from '../lib/payload';
import { app, now } from '../state';
import { History, Queue } from './TrackList';

function feed(partial: Record<string, unknown>) {
  app.value = {
    connection: 'live',
    receivedAt: Date.now(),
    clockOffsetMs: 0,
    listenerDelayMs: 0,
    data: parsePayload({ system_status: 'online', current: null, ...partial }),
  };
}

beforeEach(() => {
  now.value = Date.parse('2026-09-22T12:00:00Z');
});

describe('Queue', () => {
  it('shows a queued break first and the song after it', () => {
    feed({
      breaks_queue: [{ asset_id: 'b', title: 'Station ID 0x1', source: 'bumper', duration_sec: 5 }],
      music_queue: [{ asset_id: 'm', title: 'Song', artist: 'A', source: 'music', duration_sec: 200 }],
    });
    render(<Queue />);
    expect(screen.getByText('Station ID 0x1')).toBeInTheDocument();
    expect(screen.getByText('↳ then Song')).toBeInTheDocument();
    expect(screen.getByText('Station ID 0x1').closest('[data-kind]')).toHaveAttribute('data-kind', 'bumper');
  });

  it('renders feed text literally, never as markup', () => {
    feed({
      music_queue: [
        { asset_id: 'm', title: '<img src=x onerror=alert(1)> & "Friends"', artist: '<b>bold</b>', source: 'music' },
      ],
    });
    const { container } = render(<Queue />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('b')).toBeNull();
    expect(screen.getByText('<img src=x onerror=alert(1)> & "Friends"')).toBeInTheDocument();
  });

  it('explains an empty queue', () => {
    feed({});
    render(<Queue />);
    expect(screen.getByText(/Queue empty/)).toBeInTheDocument();
  });
});

describe('History', () => {
  it('shows relative times that follow the shared clock', async () => {
    feed({
      history: [
        { asset_id: 'a', title: 'News', source: 'break', played_at: '2026-09-22T11:55:00Z' },
        { asset_id: 'b', title: 'Song', source: 'music', played_at: '2026-09-22T10:00:00Z' },
      ],
    });
    render(<History />);
    expect(screen.getByText('5m ago')).toBeInTheDocument();
    expect(screen.getByText('2h ago')).toBeInTheDocument();
    now.value = Date.parse('2026-09-22T12:10:00Z');
    await waitFor(() => expect(screen.getByText('15m ago')).toBeInTheDocument());
  });
});
