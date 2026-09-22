import { fireEvent, render, screen } from '@testing-library/preact';
import { useState } from 'preact/hooks';
import { describe, expect, it, vi } from 'vitest';
import { bus } from '../../engine/bus';
import { Spring } from '../../engine/spring';
import { CarrierMeter, Fader, LatchButton, Meter, PositionMeter, RotarySwitch } from '.';
import { carrierTarget } from './meters';
import { detentAngle } from './RotarySwitch';
import { carrierScale, labelsCollide, positionScale, vuScale } from './scale';

describe('scale specs', () => {
  const specs = {
    vu: vuScale,
    carrier: carrierScale,
    short: positionScale(21.5, 0),
    song: positionScale(213.6, 4),
    hour: positionScale(3725, 0),
  };
  it.each(Object.entries(specs))('%s labels never overprint, full or compact', (_, spec) => {
    expect(labelsCollide(spec, false)).toBe(false);
    expect(labelsCollide(spec, true)).toBe(false);
  });
  it('ticks stay on the arc and the crossfade red zone sits at the end', () => {
    for (const s of Object.values(specs))
      for (const t of s.ticks(false)) {
        expect(t.p).toBeGreaterThanOrEqual(0);
        expect(t.p).toBeLessThanOrEqual(1.0001);
      }
    expect(positionScale(200, 4).red?.[0]).toBeCloseTo(0.98, 3);
    expect(positionScale(200, 0).red).toBeNull();
    expect(positionScale(0, 4).red).toBeNull();
    expect(
      positionScale(213, 0)
        .labels(false)
        .map((l) => l.text),
    ).toEqual(['0:00', '0:53', '1:46', '2:39', '3:33']);
  });
});

describe('Meter', () => {
  it('is an accessible meter whose face is decorative', () => {
    render(
      <Meter
        title="Level"
        tri={{ zh: '电平' }}
        spec={vuScale}
        spring={new Spring({ w: 1, z: 1 }, 0)}
        caption="idle"
        value={-7}
        min={-20}
        max={3}
        valueText="-7 VU"
      />,
    );
    const m = screen.getByRole('meter', { name: 'Level' });
    expect(m).toHaveAttribute('aria-valuenow', '-7');
    expect(m).toHaveAttribute('aria-valuetext', '-7 VU');
    expect(m.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    expect(m.querySelectorAll('.scale-num')).toHaveLength(5);
  });
  it('kicks its needle when the chassis thumps', () => {
    const s = new Spring({ w: 1, z: 1 }, 0);
    render(
      <Meter
        title="T"
        tri={{ zh: '电平' }}
        spec={vuScale}
        spring={s}
        caption=""
        thump={{ press: 0.5, relay: 2 }}
        value={0}
        valueText=""
      />,
    );
    bus.thump('press');
    bus.thump('relay');
    expect(s.v).toBeCloseTo(2.5);
  });
  it('position meter reads elapsed of total', () => {
    render(<PositionMeter durationSec={213} crossfadeSec={4} elapsed={() => 83} elapsedNow={83} />);
    expect(screen.getByRole('meter', { name: 'Position' })).toHaveAttribute('aria-valuetext', '1:23 of 3:33');
    expect(screen.getByText('red · 4 s crossfade')).toBeInTheDocument();
  });
  it('carrier meter follows connection state', () => {
    const { rerender } = render(<CarrierMeter conn="live" />);
    expect(screen.getByText('feed health')).toBeInTheDocument();
    rerender(<CarrierMeter conn="nosignal" />);
    expect(screen.getByRole('meter', { name: 'Carrier' })).toHaveAttribute('aria-valuetext', 'no carrier');
    expect(carrierTarget('live', 1)).toBeGreaterThan(0.8);
    expect(carrierTarget('nosignal', 1)).toBeLessThan(0);
  });
});

describe('LatchButton', () => {
  it('names its state and latches', () => {
    const onPress = vi.fn();
    const { rerender } = render(<LatchButton state="idle" onPress={onPress} />);
    const b = screen.getByRole('button', { name: /Tune in/ });
    expect(b).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(b);
    expect(onPress).toHaveBeenCalledOnce();
    rerender(<LatchButton state="loading" sub="Hopping to 96k" onPress={onPress} />);
    expect(screen.getByRole('button', { name: /Locking/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Hopping to 96k')).toBeInTheDocument();
    rerender(<LatchButton state="error" onPress={onPress} />);
    expect(screen.getByRole('button', { name: /No carrier/ })).toHaveAttribute('aria-pressed', 'false');
  });
  it('strikes the readout and thumps the meters when it goes on, fades when it goes off', () => {
    const thumps: string[] = [];
    const off = bus.onThump((k) => thumps.push(k));
    const { rerender } = render(<LatchButton state="idle" onPress={() => undefined} />);
    rerender(<LatchButton state="loading" onPress={() => undefined} />);
    expect(thumps).toEqual(['press']);
    expect(bus.power.active).toBe(true);
    rerender(<LatchButton state="idle" onPress={() => undefined} />);
    expect(bus.power.active).toBe(true); // fading down
    off();
  });
});

describe('Fader', () => {
  it('is a native slider that reports 0..100', () => {
    const onInput = vi.fn();
    render(<Fader value={80} onInput={onInput} />);
    const s = screen.getByRole('slider', { name: 'Listening level' });
    fireEvent.input(s, { target: { value: '35' } });
    expect(onInput).toHaveBeenCalledWith(35);
  });
  it('parks with a reason where volume is device-controlled', () => {
    render(<Fader value={80} onInput={() => undefined} disabled />);
    expect(screen.getByRole('slider')).toBeDisabled();
    expect(screen.getByRole('slider')).toHaveAccessibleDescription(/device's volume/);
  });
});

describe('RotarySwitch', () => {
  function Harness() {
    const [v, setV] = useState('/radio-128');
    return (
      <RotarySwitch
        legend="Feed kbps"
        tri={{ zh: '码率' }}
        name="q"
        options={[
          { value: '/radio-96', label: '96' },
          { value: '/radio-128', label: '128' },
          { value: '/radio', label: '192' },
        ]}
        value={v}
        onChange={setV}
      />
    );
  }
  it('is a labelled radio group; the knob steps to the next detent', () => {
    const { container } = render(<Harness />);
    expect(screen.getByRole('group', { name: /Feed kbps/ })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '128' })).toBeChecked();
    fireEvent.click(screen.getByRole('radio', { name: '192' }));
    expect(screen.getByRole('radio', { name: '192' })).toBeChecked();
    fireEvent.click(container.querySelector('.knob')!);
    expect(screen.getByRole('radio', { name: '96' })).toBeChecked();
    expect(screen.getByRole('radio', { name: '96' })).toHaveFocus();
  });
  it('spreads detents symmetrically', () => {
    expect([0, 1, 2].map((i) => detentAngle(i, 3))).toEqual([-52, 0, 52]);
  });
});
