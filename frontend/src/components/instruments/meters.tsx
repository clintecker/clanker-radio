import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { bus } from '../../engine/bus';
import { loop } from '../../engine/loop';
import { Spring, type SpringSpec } from '../../engine/spring';
import { ProgramLevel, VU_REST, VU_SPRING, vuP } from '../../engine/vu';
import { formatClock } from '../../lib/format';
import type { TrackKind } from '../../lib/types';
import { Meter } from './Meter';
import { carrierScale, positionScale, vuScale } from './scale';

const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
const REST = VU_REST;

/** Keep the latest props in a ref so the frame callback never goes stale and never re-subscribes. */
function useLatest<T>(v: T) {
  const r = useRef(v);
  r.current = v;
  return r;
}

export type AnalyserSource = () => AnalyserNode | null;

export interface VuMeterProps {
  /** Needle is driven only while audio is actually playing. */
  active: boolean;
  kind: TrackKind;
  /** Real program tap; return null to use the program model. */
  analyser: AnalyserSource;
}

export function VuMeter({ active, kind, analyser }: VuMeterProps) {
  const spring = useMemo(() => new Spring(VU_SPRING, REST), []);
  const level = useMemo(() => new ProgramLevel(), []);
  const props = useLatest({ active, kind, analyser });
  const [source, setSource] = useState<'idle' | 'real' | 'simulated'>('idle');
  const [db, setDb] = useState(-Infinity);

  useEffect(() => {
    if (active) level.reset();
  }, [active, level]);

  useEffect(() => {
    let lastPublish = 0;
    let src: 'idle' | 'real' | 'simulated' = 'idle';
    let lastDb = -Infinity;
    return loop.add((dt, now) => {
      const p = props.current;
      if (p.active) {
        const r = level.read(now / 1000, dt, p.kind, p.analyser());
        lastDb = clamp(r.db, -40, 4);
        spring.target = vuP(lastDb);
        src = r.real ? 'real' : 'simulated';
      } else {
        spring.target = REST;
        lastDb = -Infinity;
        src = 'idle';
      }
      bus.level = clamp(spring.x, 0, 1);
      bus.source = src;
      if (now - lastPublish > 250) {
        lastPublish = now;
        setSource(src);
        setDb(Number.isFinite(lastDb) ? Math.round(lastDb) : -Infinity);
      }
    });
  }, [level, props, spring]);

  const caption =
    source === 'idle' ? 'idle · tune in to drive' : source === 'real' ? 'program · live' : 'program · simulated';
  return (
    <Meter
      class="m-vu"
      title="Level"
      tri={{ zh: '电平', id: 'Level', ru: 'Уровень' }}
      spec={vuScale}
      spring={spring}
      thump={THUMP_VU}
      caption={caption}
      value={Number.isFinite(db) ? db : -20}
      min={-20}
      max={3}
      valueText={Number.isFinite(db) ? `${db} VU` : 'no signal'}
    />
  );
}
const THUMP_VU = { press: 0.9, relay: 7.5 };
const THUMP_OTHER = { press: 0.35, relay: 0 };

export interface PositionMeterProps {
  durationSec: number;
  crossfadeSec: number;
  /** Elapsed seconds on the server clock; read every frame. */
  elapsed: () => number;
  /** Elapsed seconds for the accessible value (data rate). */
  elapsedNow: number;
}

export function PositionMeter({ durationSec, crossfadeSec, elapsed, elapsedNow }: PositionMeterProps) {
  const read = useLatest({ elapsed, durationSec });
  const frac = () =>
    read.current.durationSec > 0 ? clamp(read.current.elapsed() / read.current.durationSec, 0, 1) : 0;
  const spring = useMemo(() => new Spring(POS_SPRING, frac()), []);
  useEffect(() => loop.add(() => void (spring.target = frac())), [spring]);
  const spec = useMemo(() => positionScale(durationSec, crossfadeSec), [durationSec, crossfadeSec]);
  return (
    <Meter
      class="m-pos"
      title="Position"
      tri={{ zh: '进度', id: 'Posisi', ru: 'Позиция' }}
      spec={spec}
      spring={spring}
      thump={THUMP_OTHER}
      caption={crossfadeSec > 0 ? `red · ${crossfadeSec.toFixed(0)} s crossfade` : 'no crossfade'}
      value={durationSec > 0 ? clamp(elapsedNow / durationSec, 0, 1) : 0}
      valueText={durationSec > 0 ? `${formatClock(elapsedNow)} of ${formatClock(durationSec)}` : 'unknown length'}
    />
  );
}
const POS_SPRING: SpringSpec = { w: 5.5, z: 0.86, min: REST, max: 1.06, restitution: 0.28 };
const CAR_SPRING: SpringSpec = { w: 6, z: 0.55, min: REST, max: 1.06, restitution: 0.28 };

export type CarrierState = 'live' | 'reconnecting' | 'nosignal';

export function carrierTarget(conn: CarrierState, t: number): number {
  if (conn === 'live') return 0.86 + 0.025 * Math.sin(t * 1.4) + 0.012 * Math.sin(t * 5.7);
  if (conn === 'reconnecting') return 0.32 + 0.22 * Math.sin(t * 4.1) * Math.sin(t * 1.7);
  return REST;
}

export function CarrierMeter({ conn }: { conn: CarrierState }) {
  const spring = useMemo(() => new Spring(CAR_SPRING, conn === 'live' ? 0.86 : REST), []);
  const read = useLatest(conn);
  useEffect(() => loop.add((_, now) => void (spring.target = carrierTarget(read.current, now / 1000))), [spring, read]);
  const caption = conn === 'live' ? 'feed health' : conn === 'reconnecting' ? 'jammed · reacquiring' : 'carrier lost';
  return (
    <Meter
      class="m-car"
      title="Carrier"
      tri={{ zh: '载波', id: 'Pembawa', ru: 'Несущая' }}
      spec={carrierScale}
      spring={spring}
      thump={THUMP_OTHER}
      caption={caption}
      value={conn === 'live' ? 0.86 : conn === 'reconnecting' ? 0.32 : 0}
      valueText={conn === 'live' ? 'carrier holding' : conn === 'reconnecting' ? 'carrier jammed' : 'no carrier'}
    />
  );
}
