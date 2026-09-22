import { describe, expect, it } from 'vitest';
import { formatBulletinTime, parseArchive } from './archive';

describe('parseArchive', () => {
  it('keeps well-formed entries', () => {
    const idx = parseArchive({
      generated_at: 'x',
      count: 1,
      breaks: [{ filename: 'b.mp3', timestamp: '2026-09-22T11:07:47', url: '/api/breaks/b.mp3', size_bytes: 10 }],
    });
    expect(idx.breaks).toHaveLength(1);
    expect(idx.count).toBe(1);
  });
  it('drops entries pointing outside the archive endpoint', () => {
    const idx = parseArchive({
      breaks: [
        { timestamp: 't', url: 'https://evil.example/x.mp3' },
        { timestamp: 't', url: '/api/breaks/../../etc/passwd' },
        { timestamp: 't', url: '/api/breaks/ok.mp3' },
      ],
    });
    expect(idx.breaks.map((b) => b.url)).toEqual(['/api/breaks/ok.mp3']);
  });
  it('rejects non-objects', () => {
    expect(() => parseArchive('nope')).toThrow();
  });
});

describe('formatBulletinTime', () => {
  it('formats the station wall clock without timezone conversion', () => {
    expect(formatBulletinTime('2026-09-22T11:07:47')).toBe('Sep 22, 11:07');
    expect(formatBulletinTime('garbage')).toBe('garbage');
  });
});
