import { describe, expect, it } from 'vitest';
import { formatClock, formatTimeAgo, formatUptime, normalizeIso } from './format';

describe('formatClock', () => {
  it('formats whole minutes and seconds', () => {
    expect(formatClock(0)).toBe('0:00');
    expect(formatClock(65)).toBe('1:05');
    expect(formatClock(211.632)).toBe('3:31');
  });
  it('handles missing or bad values', () => {
    expect(formatClock(null)).toBe('0:00');
    expect(formatClock(NaN)).toBe('0:00');
    expect(formatClock(-3)).toBe('0:00');
  });
});

describe('formatTimeAgo', () => {
  const now = new Date('2026-09-22T12:00:00Z');
  it('buckets into now / minutes / hours / days', () => {
    expect(formatTimeAgo(new Date('2026-09-22T11:59:30Z'), now)).toBe('just now');
    expect(formatTimeAgo(new Date('2026-09-22T11:45:00Z'), now)).toBe('15m ago');
    expect(formatTimeAgo(new Date('2026-09-22T09:00:00Z'), now)).toBe('3h ago');
    expect(formatTimeAgo(new Date('2026-09-19T09:00:00Z'), now)).toBe('3d ago');
  });
  it('never goes negative for slightly-future timestamps', () => {
    expect(formatTimeAgo(new Date('2026-09-22T12:00:05Z'), now)).toBe('just now');
  });
});

describe('formatUptime', () => {
  const now = new Date('2026-09-22T12:00:00Z');
  it('shows hours and minutes under a day, days and hours above', () => {
    expect(formatUptime('2026-09-22T09:30:00Z', now)).toBe('2h 30m');
    expect(formatUptime('2026-09-19T04:57:53+00:00', now)).toBe('3d 7h');
  });
  it('accepts the icecast offset format without a colon', () => {
    expect(formatUptime(normalizeIso('2026-09-22T09:30:00+0000'), now)).toBe('2h 30m');
  });
  it('is a dash when unknown', () => {
    expect(formatUptime(undefined, now)).toBe('—');
    expect(formatUptime('garbage', now)).toBe('—');
  });
});
