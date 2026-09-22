import { render, screen, waitFor, within } from '@testing-library/preact';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ConnectionState } from '../../lib/types';
import { ConsoleArchive } from '../../pages/console/ConsoleArchive';
import { app, now } from '../../state';
import { Bulletins, Log, MeterBay, NextUp, OnAir, ServicePanel, StatusStrip } from '.';
import { connOverride } from './console-state';
import { CJK, CYRILLIC, LONG, NOW, TAGGED, fixture } from './fixtures';
import {
  carrierOf,
  carrierUptime,
  feedRates,
  listenerCount,
  listenerPeak,
  odometer,
  queueOf,
  artistLine,
} from './select';

function feed(over: Record<string, unknown> = {}, connection: ConnectionState = 'live') {
  app.value = { connection, receivedAt: NOW, clockOffsetMs: 0, data: fixture(over) };
}

beforeEach(() => {
  now.value = NOW;
  connOverride.value = null;
  feed();
});
afterEach(() => vi.unstubAllGlobals());

describe('selectors', () => {
  it('ignore the fallback mount when counting listeners', () => {
    const p = fixture();
    expect(listenerCount(p)).toBe(7);
    expect(listenerPeak(p)).toBe(9);
    expect(feedRates(p)).toBe('96 / 128 / 192');
    expect(carrierUptime(p, NOW)).toBe('3d 12h 12m');
    expect(carrierUptime(null, NOW)).toBe('—');
  });
  it('map feed health to three carrier states', () => {
    expect(carrierOf('live')).toBe('live');
    expect(carrierOf('connecting')).toBe('reconnecting');
    expect(carrierOf('restarting')).toBe('reconnecting');
    expect(carrierOf('stale')).toBe('nosignal');
  });
  it('format odometer, artist line and queue', () => {
    expect(odometer(7)).toEqual(['00', '7']);
    expect(odometer(12345)).toEqual(['', '999']);
    expect(artistLine({ asset_id: 'a', title: 't', artist: 'A', album: 'B', duration_sec: 1, source: 'music' })).toBe(
      'A · B',
    );
    expect(queueOf(fixture()).total).toBe(3);
    expect(queueOf(null).total).toBe(0);
  });
});

describe('StatusStrip', () => {
  it('shows carrier, listeners, UTC clock and a session key', () => {
    render(<StatusStrip />);
    expect(screen.getByRole('status')).toHaveTextContent('Holding');
    expect(screen.getByLabelText('7 listening')).toBeInTheDocument();
    expect(screen.getByRole('timer')).toHaveTextContent('17:10:49');
    expect(screen.getByLabelText(/Session key/).textContent).toMatch(/^[0-9A-F]{4}·[0-9A-F]{4}·[0-9A-F]{4}$/);
  });
  it('speaks in operator voice when the carrier drops', () => {
    feed({}, 'stale');
    const { container } = render(<StatusStrip />);
    expect(screen.getByRole('status')).toHaveTextContent('No carrier');
    expect(container.querySelector('.c-car')).toHaveAttribute('data-conn', 'nosignal');
  });
});

describe('OnAir', () => {
  it('renders a long title as text with elapsed/remaining on the server clock', () => {
    render(<OnAir />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(LONG);
    expect(screen.getByTestId('elapsed')).toHaveTextContent('1:00');
    expect(screen.getByText('−2:33')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '28');
    expect(screen.getByRole('button', { name: /Tune in/ })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('radio', { name: '128' })).toBeChecked();
  });
  it('keeps tags in titles literal and lights the right kind lamp', () => {
    feed({
      current: {
        asset_id: 'b',
        title: TAGGED,
        artist: 'Newsroom',
        source: 'break',
        duration_sec: 90,
        played_at: '2026-09-22T17:10:00Z',
      },
    });
    const { container } = render(<OnAir />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(TAGGED);
    expect(container.querySelector('main b, .readout b, .readout img')).toBeNull();
    expect(container.querySelector('.readout')).toHaveAttribute('data-kind', 'break');
    expect(container.querySelector('.kind.lit')).toHaveTextContent('News bulletin');
    expect(screen.getByText('Bulletin interrupt · news')).toBeInTheDocument();
  });
  it('explains an empty feed instead of showing a blank', () => {
    feed({ current: null }, 'stale');
    const { container } = render(<OnAir />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('No signal');
    expect(container.querySelector('.readout')).toHaveClass('jam');
  });
});

describe('queue and log', () => {
  it('lists cut-ins first, CJK and tagged titles as text', () => {
    render(<NextUp />);
    expect(screen.getByText('3 queued')).toBeInTheDocument();
    expect(screen.getByText('Cut in before the next song')).toBeInTheDocument();
    expect(screen.getByText(CJK)).toBeInTheDocument();
    expect(screen.getByText(TAGGED)).toBeInTheDocument();
    expect(screen.getByText('Station ID')).toBeInTheDocument();
  });
  it('says the queue is dry', () => {
    feed({ breaks_queue: [], music_queue: [] });
    render(<NextUp />);
    expect(screen.getByText(/Queue dry/)).toBeInTheDocument();
  });
  it('logs plays with relative times and kinds', () => {
    const { container } = render(<Log />);
    expect(screen.getByText(CYRILLIC)).toBeInTheDocument();
    expect(screen.getByText('7m ago')).toBeInTheDocument();
    expect(screen.getByText('last 2 plays')).toBeInTheDocument();
    expect(container.querySelector('.row[data-kind="break"]')).toHaveTextContent('News bulletin');
  });
  it('explains a wiped log', () => {
    feed({ history: [] });
    render(<Log />);
    expect(screen.getByText(/Log wiped/)).toBeInTheDocument();
  });
});

describe('MeterBay and ServicePanel', () => {
  it('shows three meters with accessible values', () => {
    render(<MeterBay />);
    expect(screen.getByRole('meter', { name: 'Level' })).toHaveAttribute('aria-valuetext', 'no signal');
    expect(screen.getByRole('meter', { name: 'Position' })).toHaveAttribute('aria-valuetext', '1:00 of 3:33');
    expect(screen.getByRole('meter', { name: 'Carrier' })).toHaveAttribute('aria-valuetext', 'carrier holding');
  });
  it('reports icecast figures, and no debug keys by default', () => {
    render(<ServicePanel />);
    expect(screen.getByText('96 / 128 / 192')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Save .m3u' })).toHaveAttribute('download');
    expect(screen.queryByRole('button', { name: /Drop signal/ })).toBeNull();
  });
});

describe('bulletins', () => {
  const index = {
    breaks: Array.from({ length: 5 }, (_, i) => ({
      filename: `b${i}.mp3`,
      timestamp: `2026-09-22T${String(16 - i).padStart(2, '0')}:00:07`,
      url: `/api/breaks/b${i}.mp3`,
      size_bytes: 1_700_000,
    })),
  };
  it('shows three reels and expands the rest in place', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify(index)))),
    );
    render(<Bulletins />);
    await waitFor(() => expect(screen.getByText('16:00')).toBeInTheDocument());
    const more = screen.getByRole('button', { name: /Archive ▸ 2 more/ });
    expect(more).toHaveAttribute('aria-expanded', 'false');
    more.click();
    await waitFor(() => expect(more).toHaveAttribute('aria-expanded', 'true'));
    expect(screen.getByText('12:00')).toBeVisible();
    screen.getByRole('button', { name: 'Play the 16:00 bulletin' }).click();
    await waitFor(() => expect(screen.getByLabelText('16:00 bulletin')).toHaveAttribute('src', '/api/breaks/b0.mp3'));
  });
  it('archive page lists every reel; an outage is explained', async () => {
    vi.stubGlobal(
      'EventSource',
      class {
        static CLOSED = 2;
        close = vi.fn();
        addEventListener = vi.fn();
      },
    );
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify(index)))),
    );
    const { unmount } = render(<ConsoleArchive />);
    await waitFor(() => expect(screen.getByText('5 reels · last 24 h')).toBeInTheDocument());
    expect(within(screen.getByRole('region', { name: /Bulletin archive/ })).getAllByRole('listitem')).toHaveLength(5);
    unmount();
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('no', { status: 503 }))),
    );
    render(<Bulletins />);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('HTTP 503'));
  });
});
