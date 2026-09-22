/**
 * Server clock offset estimation.
 *
 * Every payload carries `updated_at` stamped by the server. The message with the
 * smallest apparent transit delay gives the best offset estimate, so we keep the
 * minimum-latency sample (classic NTP-style reasoning) and let it decay slowly
 * so a one-off fast packet does not pin the estimate forever.
 */
export class ClockSync {
  private best: { offset: number; at: number } | null = null;
  private static readonly DECAY_MS = 10 * 60_000;

  /** Feed one server timestamp received at client time `receivedAt` (ms). Returns the current offset. */
  sample(serverIso: string, receivedAt: number): number {
    const serverMs = Date.parse(serverIso);
    if (Number.isNaN(serverMs)) return this.offset();
    const offset = serverMs - receivedAt; // negative means the packet took time to arrive (or clocks differ)
    if (!this.best || offset > this.best.offset || receivedAt - this.best.at > ClockSync.DECAY_MS) {
      this.best = { offset, at: receivedAt };
    }
    return this.offset();
  }

  offset(): number {
    return this.best?.offset ?? 0;
  }
}
