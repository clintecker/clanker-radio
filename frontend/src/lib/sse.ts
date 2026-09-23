import { STALE_AFTER_MS } from './config';
import { AudibleQueue } from './audible';
import { ClockSync } from './clock';
import type { Store } from './store';
import { parsePayload } from './payload';

/**
 * Keeps one EventSource open to the push daemon and mirrors its health into the store.
 *
 * The browser's EventSource already reconnects on its own with backoff, so we never
 * close it on error. What the browser does NOT do is tell us when the connection
 * is silently dead (e.g. a proxy holding the socket open), so a watchdog marks the
 * feed stale if neither data nor a keepalive comment arrives for STALE_AFTER_MS,
 * and then forces a fresh connection.
 */
export class FeedConnection {
  private source: EventSource | null = null;
  private watchdog: number | null = null;
  private lastActivity = 0;
  private lastOpenAt = 0;
  /** The first message after (re)connect is the daemon's cached state; its updated_at is stale. */
  private awaitingFirstMessage = true;
  private reconnectAttempts = 0;
  private badMessages = 0;
  private readonly clock = new ClockSync();
  /** Payloads wait here until this listener can hear them (on_air_at + playback delay). */
  private readonly audible: AudibleQueue;

  constructor(
    private readonly url: string,
    private readonly store: Store,
  ) {
    this.audible = new AudibleQueue(
      { serverNow: () => store.serverNow(), delayMs: () => store.get().listenerDelayMs },
      (data) => this.store.update({ data }),
    );
    // Tuning in or out changes the delay: re-time whatever is still pending.
    store.subscribe((s, prev) => {
      if (s.listenerDelayMs !== prev.listenerDelayMs) this.audible.flush();
    });
  }

  start(): void {
    this.open();
    this.watchdog = window.setInterval(() => this.checkStale(), 5_000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') this.checkStale(true);
    });
  }

  private open(): void {
    this.source?.close();
    // A stale feed stays NO SIGNAL until data actually flows again.
    const current = this.store.get().connection;
    if (current !== 'stale') this.store.update({ connection: this.store.get().data ? 'reconnecting' : 'connecting' });
    const es = new EventSource(this.url);
    this.source = es;
    this.lastActivity = Date.now();
    this.lastOpenAt = this.lastActivity;
    this.awaitingFirstMessage = true;

    es.onopen = () => {
      this.lastActivity = Date.now();
      this.store.update({ connection: 'live' });
    };
    es.onmessage = (ev: MessageEvent<string>) => this.handleMessage(ev.data);
    es.addEventListener('ping', () => {
      this.lastActivity = Date.now();
      if (this.store.get().connection === 'stale') this.store.update({ connection: 'live' });
    });
    es.onerror = () => {
      // readyState CLOSED means the browser gave up (e.g. HTTP 4xx/5xx); reopen ourselves.
      this.store.update({ connection: 'reconnecting' });
      if (es.readyState === EventSource.CLOSED) window.setTimeout(() => this.open(), this.nextBackoffMs());
    };
  }

  private handleMessage(raw: string): void {
    const receivedAt = Date.now();
    this.lastActivity = receivedAt;
    let data;
    try {
      data = parsePayload(JSON.parse(raw));
    } catch (err) {
      // A bad message must not take the page down; the previous state stays on screen.
      console.error('Ignoring unusable SSE payload', err);
      this.badMessages += 1;
      return;
    }
    this.badMessages = 0;
    this.reconnectAttempts = 0;
    // server_time is stamped as each message is sent, so every message is a clock
    // sample. Older daemons only had updated_at, stamped at export time, which is
    // only trustworthy on live broadcasts (not the replayed initial state).
    const isLiveBroadcast = !this.awaitingFirstMessage;
    this.awaitingFirstMessage = false;
    const stamp = data.server_time ?? (isLiveBroadcast ? data.updated_at : '');
    const clockOffsetMs = stamp ? this.clock.sample(stamp, receivedAt) : this.store.get().clockOffsetMs;
    const connection = data.system_status === 'restarting' ? 'restarting' : 'live';
    this.store.update({ receivedAt, clockOffsetMs, connection });
    this.audible.push(data);
  }

  /** Exponential backoff with jitter: 2s, 4s, 8s … capped at 60s. Reset on any good message. */
  private nextBackoffMs(): number {
    const base = Math.min(60_000, 2_000 * 2 ** Math.min(this.reconnectAttempts, 5));
    this.reconnectAttempts += 1;
    return base / 2 + (Math.random() * base) / 2;
  }

  private checkStale(force = false): void {
    const now = Date.now();
    const silentFor = now - this.lastActivity;
    if (!force && silentFor <= STALE_AFTER_MS) return;
    if (this.store.get().connection !== 'stale') this.store.update({ connection: 'stale' });
    // Reopen at most once per stale window so a dead server is not hammered every 5s.
    if (force || now - this.lastOpenAt > STALE_AFTER_MS) this.open();
  }

  /** Test/diagnostic hook: how many consecutive messages were unparseable. */
  get unusableMessages(): number {
    return this.badMessages;
  }

  stop(): void {
    this.audible.clear();
    this.source?.close();
    if (this.watchdog) window.clearInterval(this.watchdog);
  }
}
