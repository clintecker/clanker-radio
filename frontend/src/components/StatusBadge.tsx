import { app, now } from '../state';
import type { ConnectionState } from '../lib/types';

const LABELS: Record<ConnectionState, string> = {
  connecting: 'TUNING',
  live: 'LIVE',
  reconnecting: 'RECONNECTING',
  stale: 'NO SIGNAL',
  restarting: 'RESTARTING',
};

const DOT: Record<ConnectionState, string> = {
  connecting: 'bg-amber text-amber [animation-duration:.6s]',
  live: 'bg-phosphor text-phosphor',
  reconnecting: 'bg-amber text-amber [animation-duration:.6s]',
  stale: 'bg-alarm text-alarm animate-none',
  restarting: 'bg-amber text-amber [animation-duration:.4s]',
};

/** Honest about the feed: says LIVE only while data is actually flowing. */
export function StatusBadge() {
  const { connection, receivedAt } = app.value;
  const age = receivedAt ? Math.round((now.value - receivedAt) / 1000) : null;
  return (
    <span
      class={`inline-flex items-center gap-1.5 text-[0.65rem] tracking-[0.15em] ${connection === 'stale' ? 'text-alarm' : ''}`}
      data-state={connection}
      title={age === null ? 'Waiting for first update' : `Last update ${age}s ago`}
      role="status"
    >
      <span
        class={`h-1.5 w-1.5 rounded-full shadow-[0_0_6px_currentColor] animate-pulse-dot motion-safe-only ${DOT[connection]}`}
        aria-hidden="true"
      />
      <span id="status-text">{LABELS[connection]}</span>
    </span>
  );
}
