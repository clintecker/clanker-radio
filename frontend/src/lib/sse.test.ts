import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedConnection } from './sse';
import { Store } from './store';

/** Minimal EventSource double: tests drive open/message/error/ping by hand. */
class FakeEventSource extends EventTarget {
  static instances: FakeEventSource[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  constructor(public url: string) {
    super();
    FakeEventSource.instances.push(this);
  }
  close() {
    this.closed = true;
    this.readyState = 2;
  }
  // test helpers
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  message(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: typeof data === 'string' ? data : JSON.stringify(data) }));
  }
  ping() {
    this.dispatchEvent(new Event('ping'));
  }
  fail(closed: boolean) {
    this.readyState = closed ? 2 : 0;
    this.onerror?.();
  }
}

const payload = (title: string, updated_at = '2026-09-22T12:00:00Z') => ({
  updated_at,
  system_status: 'online',
  current: { asset_id: title, title, source: 'music' },
  breaks_queue: [],
  music_queue: [],
  history: [],
});

describe('FeedConnection', () => {
  let store: Store;
  let feed: FeedConnection;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-22T12:00:00Z'));
    FakeEventSource.instances = [];
    vi.stubGlobal('EventSource', FakeEventSource);
    store = new Store();
    feed = new FeedConnection('/api/stream', store);
    feed.start();
  });
  afterEach(() => {
    feed.stop();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  const es = () => FakeEventSource.instances.at(-1)!;

  it('starts connecting, goes live on open, and stores parsed data', () => {
    expect(store.get().connection).toBe('connecting');
    es().open();
    expect(store.get().connection).toBe('live');
    es().message(payload('One'));
    expect(store.get().data?.current?.title).toBe('One');
  });

  it('keeps the last good state when a message is garbage', () => {
    es().open();
    es().message(payload('One'));
    es().message('<html>502 Bad Gateway</html>');
    es().message({ nonsense: true });
    expect(store.get().data?.current?.title).toBe('One');
    expect(feed.unusableMessages).toBe(2);
  });

  it('does not use the replayed initial state as a clock sample', () => {
    es().open();
    // Replayed state from 10 minutes ago: must not pull the clock 10 minutes back.
    es().message(payload('Old', '2026-09-22T11:50:00Z'));
    expect(store.get().clockOffsetMs).toBe(0);
    vi.setSystemTime(new Date('2026-09-22T12:00:05Z'));
    es().message(payload('Live', '2026-09-22T12:00:05.000Z'));
    expect(Math.abs(store.get().clockOffsetMs)).toBeLessThan(50);
  });

  it('marks the feed stale when neither data nor pings arrive, and reopens once', () => {
    es().open();
    es().message(payload('One'));
    const first = es();
    vi.advanceTimersByTime(60_000);
    es().ping();
    vi.advanceTimersByTime(60_000); // 60s since ping: fine
    expect(store.get().connection).toBe('live');
    vi.advanceTimersByTime(80_000); // 140s since ping: stale
    expect(store.get().connection).toBe('stale');
    expect(first.closed).toBe(true);
    expect(FakeEventSource.instances).toHaveLength(2);
    vi.advanceTimersByTime(10_000); // still stale, but no second reopen inside the window
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it('reports reconnecting on browser-side errors and backs off when the browser gives up', () => {
    es().open();
    es().fail(false); // browser will retry itself
    expect(store.get().connection).toBe('reconnecting');
    expect(FakeEventSource.instances).toHaveLength(1);
    es().fail(true); // browser gave up: we reopen after backoff
    vi.advanceTimersByTime(2_100);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it('reflects a restarting daemon', () => {
    es().open();
    es().message({ ...payload('One'), system_status: 'restarting' });
    expect(store.get().connection).toBe('restarting');
  });
});
