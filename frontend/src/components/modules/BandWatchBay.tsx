import { app, playerState } from '../../state';
import { BandWatch } from '../instruments';
import { Legend } from '../primitives/Legend';
import { Panel } from '../primitives/Panel';
import { Sticker } from '../primitives/Sticker';
import { carrier, programTap } from './console-state';
import { BAND_MESSAGE, sources } from './select';

/** The signature: a live spectrum/waterfall of the station's band, above everything else. */
export function BandWatchBay() {
  const car = carrier.value;
  const selected = playerState.value?.stream.bitrate ?? 128;
  const carriers = [...new Set(sources(app.value.data).map((s) => s.bitrate))];
  return (
    <Panel name="band" aria-labelledby="l-band" data-conn={car}>
      <Legend
        en="Band watch"
        zh="频段"
        id="Pita"
        ru="Диапазон"
        htmlId="l-band"
        note={
          <>
            scanning for corp jammers · <b>{selected}k</b> carrier marked
          </>
        }
      />
      <div class="window bandwin">
        <BandWatch carrier={car} carriers={carriers} selected={selected} analyser={programTap} />
        <div class="band-msg" role="status">
          {BAND_MESSAGE[car]}
        </div>
        <div class="band-scale num" aria-hidden="true">
          <span>87.5</span>
          <span>96</span>
          <span>128</span>
          <span>192</span>
          <span>MHz·ish</span>
        </div>
      </div>
      <Sticker variant="tape" style={{ right: '-6px', top: '-6px', transform: 'rotate(8deg)' }}>
        DO NOT RETUNE
      </Sticker>
      <Sticker variant="idn" style={{ left: '30px', bottom: '-8px' }}>
        ⚡ AWAS · TEGANGAN TINGGI · 高压
      </Sticker>
    </Panel>
  );
}
