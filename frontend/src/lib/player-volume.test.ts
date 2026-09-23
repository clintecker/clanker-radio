import { afterEach, describe, expect, it, vi } from 'vitest';
import { Player } from './player';

class FakeNode {
  connect = vi.fn();
}
class FakeGain extends FakeNode {
  gain = { value: 1 };
}
class FakeCtx {
  destination = {};
  createMediaElementSource = () => new FakeNode();
  createAnalyser = () => Object.assign(new FakeNode(), { fftSize: 0, smoothingTimeConstant: 0 });
  createGain = () => new FakeGain();
  resume = () => Promise.resolve();
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('volume', () => {
  it('is supported on iOS through Web Audio when the stream is CORS-readable', () => {
    vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)');
    vi.stubGlobal('AudioContext', FakeCtx);
    expect(new Player(document.createElement('audio')).volumeSupported).toBe(true);
  });

  it('moves to the gain node once the graph exists and pins element volume to 1', () => {
    vi.stubGlobal('AudioContext', FakeCtx);
    const audio = document.createElement('audio');
    const p = new Player(audio);
    p.setVolume(0.3);
    expect(audio.volume).toBeCloseTo(0.3);
    p.getAnalyser();
    p.setVolume(0.25);
    expect(audio.volume).toBe(1);
    expect((p as unknown as { gain: FakeGain }).gain.gain.value).toBeCloseTo(0.25);
  });
});
