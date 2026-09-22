import { render, screen } from '@testing-library/preact';
import { beforeEach, describe, expect, it } from 'vitest';
import { BandWatchBay } from '../modules/BandWatchBay';
import { connOverride } from '../modules/console-state';
import { fixture, NOW } from '../modules/fixtures';
import { app } from '../../state';
import { CARRIER_POS } from './BandWatch';

beforeEach(() => {
  connOverride.value = null;
  app.value = { connection: 'live', receivedAt: NOW, clockOffsetMs: 0, data: fixture() };
});

describe('BandWatch', () => {
  it('marks the selected carrier and reports the band in words', () => {
    const { container } = render(<BandWatchBay />);
    expect(screen.getByRole('status')).toHaveTextContent('Carrier holding · band clean');
    expect(screen.getByText('128k')).toBeInTheDocument();
    expect(container.querySelector('canvas')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('.band')).toHaveAttribute('data-conn', 'live');
  });
  it('shows the jammer and the dead band', () => {
    connOverride.value = 'reconnecting';
    const { rerender, container } = render(<BandWatchBay />);
    expect(screen.getByRole('status')).toHaveTextContent('Corp jammer detected');
    connOverride.value = 'stale';
    rerender(<BandWatchBay />);
    expect(screen.getByRole('status')).toHaveTextContent('No carrier');
    expect(container.querySelector('.band')).toHaveAttribute('data-conn', 'nosignal');
  });
  it('places carriers where the scale prints them', () => {
    expect(CARRIER_POS).toEqual({ 96: 0.25, 128: 0.5, 192: 0.75 });
  });
});
