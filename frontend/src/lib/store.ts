import type { ConnectionState, NowPlayingPayload } from './types';

export interface AppState {
  connection: ConnectionState;
  data: NowPlayingPayload | null;
  /** Wall-clock ms when the last data message arrived. */
  receivedAt: number | null;
  /** Estimated (serverTime - clientTime) in ms, so progress bars use the server's clock. */
  clockOffsetMs: number;
}

type Listener = (state: AppState, prev: AppState) => void;

/** Minimal observable store: one object, whole-state updates, synchronous listeners. */
export class Store {
  private state: AppState = { connection: 'connecting', data: null, receivedAt: null, clockOffsetMs: 0 };
  private listeners = new Set<Listener>();

  get(): AppState {
    return this.state;
  }

  update(patch: Partial<AppState>): void {
    const prev = this.state;
    this.state = { ...prev, ...patch };
    for (const l of this.listeners) l(this.state, prev);
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Current time on the server's clock, in ms. */
  serverNow(): number {
    return Date.now() + this.state.clockOffsetMs;
  }
}
