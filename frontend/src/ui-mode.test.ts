import { describe, expect, it } from 'vitest';
import { parseDebug } from './debug';
import { resolveUiMode } from './ui-mode';

function mem() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
}

describe('ui mode', () => {
  it('defaults to classic and remembers an explicit choice', () => {
    const s = mem();
    expect(resolveUiMode('', s)).toBe('classic');
    expect(resolveUiMode('?ui=console', s)).toBe('console');
    expect(resolveUiMode('', s)).toBe('console');
    expect(resolveUiMode('?ui=classic', s)).toBe('classic');
    expect(resolveUiMode('', s)).toBe('classic');
    expect(resolveUiMode('?ui=bogus', s)).toBe('classic');
  });
  it('survives blocked storage', () => {
    const broken = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    };
    expect(resolveUiMode('?ui=console', broken)).toBe('console');
    expect(resolveUiMode('', broken)).toBe('classic');
    expect(resolveUiMode('', null)).toBe('classic');
  });
});

describe('debug flags', () => {
  it('are all off when debug is not compiled in', () => {
    expect(parseDebug('?debug=1&playing=1&kind=break&conn=dead&vw=390', false)).toEqual({
      panel: false,
      playing: false,
      kind: null,
      conn: null,
      vw: null,
    });
  });
  it('parse and sanitise when enabled', () => {
    expect(parseDebug('?debug=1&playing=1&kind=break&conn=dead&vw=10', true)).toEqual({
      panel: true,
      playing: true,
      kind: 'break',
      conn: 'dead',
      vw: 320,
    });
    expect(parseDebug('?kind=<b>&conn=x', true)).toMatchObject({ kind: null, conn: null });
  });
});
