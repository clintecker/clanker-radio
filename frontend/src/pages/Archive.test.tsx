import { render, screen, waitFor } from '@testing-library/preact';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Archive } from './Archive';

afterEach(() => vi.unstubAllGlobals());

const respond = (body: string, status: number) => vi.fn(() => Promise.resolve(new Response(body, { status })));

describe('Archive page', () => {
  it('lists bulletins from the index', async () => {
    vi.stubGlobal(
      'fetch',
      respond(
        JSON.stringify({
          breaks: [
            { filename: 'b.mp3', timestamp: '2026-09-22T11:07:47', url: '/api/breaks/b.mp3', size_bytes: 1_777_841 },
          ],
        }),
        200,
      ),
    );
    render(<Archive />);
    await waitFor(() => expect(screen.getByText(/Sep 22, 11:07/)).toBeInTheDocument());
    expect(screen.getByText('1.7 MB')).toBeInTheDocument();
  });

  it('explains an outage without touching the live player', async () => {
    vi.stubGlobal('fetch', respond('nope', 503));
    render(<Archive />);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('HTTP 503'));
  });
});
