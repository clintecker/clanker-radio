import { app, serverNow, store } from '../../state';
import { CarrierMeter, PositionMeter, VuMeter } from '../instruments';
import { Panel } from '../primitives/Panel';
import { Sticker } from '../primitives/Sticker';
import { carrier, current, currentKind, programTap, tuneState } from './console-state';
import { crossfadeFor, elapsedSec } from './select';

/** Meter bridge: program level, track position, carrier health. Headers share a subgrid row. */
export function MeterBay() {
  const t = current.value;
  const kind = currentKind.value;
  const car = carrier.value;
  const playedAt = t?.played_at ? Date.parse(t.played_at) : NaN;
  const elapsed = () => (Number.isNaN(playedAt) ? 0 : Math.max(0, (store.serverNow() - playedAt) / 1000));
  return (
    <Panel name="meters" aria-label="Meter bridge">
      <Sticker variant="zhs" style={{ right: '34px', bottom: '-9px' }}>
        <b lang="zh">无证广播</b> SIARAN LIAR
      </Sticker>
      <div class="bridge">
        <VuMeter active={tuneState.value === 'playing' && car !== 'nosignal'} kind={kind} analyser={programTap} />
        <PositionMeter
          key={t?.asset_id}
          durationSec={t?.duration_sec ?? 0}
          crossfadeSec={crossfadeFor(app.value.data, kind)}
          elapsed={elapsed}
          elapsedNow={elapsedSec(t, serverNow.value) ?? 0}
        />
        <CarrierMeter conn={car} />
      </div>
    </Panel>
  );
}
