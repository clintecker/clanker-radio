import type { AppState } from '../lib/store';
import type { ConnectionState } from '../lib/types';
import { byId } from './dom';

const LABELS: Record<ConnectionState, string> = {
  connecting: 'TUNING',
  live: 'LIVE',
  reconnecting: 'RECONNECTING',
  stale: 'NO SIGNAL',
  restarting: 'RESTARTING',
};

/** Connection badge in the now-playing header. Honest about the feed: LIVE only while data flows. */
export function renderStatus(state: AppState): void {
  const badge = byId('system-status');
  const text = byId('status-text');
  badge.dataset.state = state.connection;
  text.textContent = LABELS[state.connection];
  const age = state.receivedAt ? Math.round((Date.now() - state.receivedAt) / 1000) : null;
  badge.title = age === null ? 'Waiting for first update' : `Last update ${age}s ago`;
}
