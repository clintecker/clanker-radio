/**
 * Shared, frame-rate state between instruments that must not go through Preact:
 * the VU needle position drives the band watch carrier, a track change pulses the band,
 * and tuning in thumps every needle through the chassis.
 */
type Thump = (amount: number) => void;

class ProgramBus {
  /** VU needle position, 0..1. */
  level = 0;
  /** Decays from 1 after a track change. */
  pulse = 0;
  /** Where the VU is reading from right now. */
  source: 'idle' | 'real' | 'simulated' = 'idle';
  private readonly thumps = new Set<Thump>();

  onThump(fn: Thump): () => void {
    this.thumps.add(fn);
    return () => this.thumps.delete(fn);
  }

  thump(amount = 1): void {
    for (const fn of this.thumps) fn(amount);
  }
}

export const bus = new ProgramBus();
