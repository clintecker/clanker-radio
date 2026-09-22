import type { ComponentChildren } from 'preact';
import { Ear, Lamp, Legend, Panel, Readout, Screw, Sticker, Tri } from '../../components/primitives';
import type { LampColour } from '../../design/kind';

/** Dev-only parts bin: every primitive and instrument in every state. Not built into production. */

const COLOURS: LampColour[] = ['amber', 'red', 'white', 'magenta', 'cyan', 'green'];

function Bin({ title, children }: { title: string; children: ComponentChildren }) {
  return (
    <Panel name={`kit-${title}`} aria-label={title}>
      <Legend en={title} zh="零件" id="Suku cadang" ru="Детали" level={2} />
      <div class="flex flex-wrap items-center gap-6">{children}</div>
    </Panel>
  );
}

export function Kit() {
  return (
    <div class="rack console">
      <Ear side="l" />
      <Ear side="r" />
      <div class="rack-inner grid gap-6">
        <h1 class="engr text-3xl">Parts bin</h1>
        <Bin title="Lamps">
          {COLOURS.map((c) => (
            <span key={c} class="engr-2 inline-flex items-center gap-2">
              <Lamp colour={c} on={false} /> <Lamp colour={c} on /> <Lamp colour={c} on size="md" />
              <Lamp colour={c} on size="sm" /> <Lamp colour={c} on size="xs" /> {c}
            </span>
          ))}
        </Bin>
        <Bin title="Screws">
          {['a', 'b', 'c', 'd', 'e'].map((s) => (
            <Screw key={s} seed={s} />
          ))}
        </Bin>
        <Bin title="Legends">
          <div class="w-full">
            <Legend en="Band watch" zh="频段" id="Pita" ru="Диапазон" note="scanning for corp jammers" />
            <Legend en="Next up" zh="下一首" id="Berikut" ru="Далее" note="3 queued" />
            <span class="engr">
              Feed kbps <Tri zh="码率" />
            </span>
          </div>
        </Bin>
        <Bin title="Readouts">
          {(['music', 'break', 'bumper', 'unknown'] as const).map((k) => (
            <Readout key={k} kind={k} scan class="p-4 min-w-[220px]">
              <div class="engr-2 dim">{k}</div>
              <div class="phos text-2xl" style={{ fontFamily: 'var(--font-display)', fontWeight: 800 }}>
                {k === 'break' ? 'Previous <b>Song</b>' : 'ЛИТАНИЯ АПТАЙМА 夜'}
              </div>
            </Readout>
          ))}
        </Bin>
        <Bin title="Stickers">
          <Sticker variant="tape" inline>
            DO NOT RETUNE
          </Sticker>
          <Sticker variant="idn" inline>
            ⚡ AWAS · TEGANGAN TINGGI · 高压
          </Sticker>
          <Sticker variant="zhs" inline>
            <b lang="zh">无证广播</b> SIARAN LIAR
          </Sticker>
          <Sticker variant="cyr" inline>
            ЭФИР НЕ ПРЕРЫВАТЬ
          </Sticker>
          <Sticker variant="asset" inline>
            <span>
              <i>TIANHE-KAIROS</i> 物流 LOGISTIK
            </span>
            <span>
              ASSET 0x4471-C · <i>资产 DO NOT REMOVE</i>
            </span>
          </Sticker>
        </Bin>
        <Bin title="Keys">
          <button class="key" type="button">
            Save .m3u
          </button>
          <button class="key warn" type="button">
            Drop signal
          </button>
          <Readout class="p-3">
            <button class="key" type="button">
              <Lamp colour="magenta" on={false} size="sm" /> Play
            </button>
          </Readout>
        </Bin>
      </div>
    </div>
  );
}
