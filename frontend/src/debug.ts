/**
 * Debug switches for the console (?debug=1 ?playing=1 ?kind= ?conn= ?vw=). Compiled in
 * only for dev builds or when VITE_ENABLE_DEBUG=1 (staging); in production the flags are
 * all off and the DebugPanel chunk is never imported.
 */
export const DEBUG_ENABLED: boolean = import.meta.env.DEV || import.meta.env.VITE_ENABLE_DEBUG === '1';

export interface DebugFlags {
  panel: boolean;
  playing: boolean;
  kind: 'break' | 'bumper' | null;
  conn: 'reconnecting' | 'dead' | null;
  vw: number | null;
}

export const NO_DEBUG: DebugFlags = { panel: false, playing: false, kind: null, conn: null, vw: null };

export function parseDebug(search: string, enabled = DEBUG_ENABLED): DebugFlags {
  if (!enabled) return NO_DEBUG;
  const p = new URLSearchParams(search);
  const kind = p.get('kind');
  const conn = p.get('conn');
  const vw = p.get('vw');
  return {
    panel: p.get('debug') === '1',
    playing: p.get('playing') === '1',
    kind: kind === 'break' || kind === 'bumper' ? kind : null,
    conn: conn === 'reconnecting' || conn === 'dead' ? conn : null,
    vw: vw ? Math.max(320, parseInt(vw, 10) || 390) : null,
  };
}
