import { describe, expect, it } from 'vitest';
import { ClockSync } from './clock';

describe('ClockSync', () => {
  it('keeps the highest offset (lowest transit delay) sample', () => {
    const c = new ClockSync();
    const server = Date.parse('2026-09-22T12:00:00.000Z');
    c.sample('2026-09-22T12:00:00.000Z', server + 400); // 400ms late
    expect(c.offset()).toBe(-400);
    c.sample('2026-09-22T12:00:10.000Z', server + 10_000 + 50); // 50ms late: better
    expect(c.offset()).toBe(-50);
    c.sample('2026-09-22T12:00:20.000Z', server + 20_000 + 900); // worse, ignored
    expect(c.offset()).toBe(-50);
  });
  it('ignores unparseable timestamps', () => {
    const c = new ClockSync();
    expect(c.sample('nope', 1000)).toBe(0);
  });
});
