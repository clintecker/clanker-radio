import { useEffect, useRef } from 'preact/hooks';
import { bus } from '../../engine/bus';
import { loop } from '../../engine/loop';
import { Scrambler } from '../../engine/scramble';
import { KIND_LABEL, KIND_LAMP } from '../../design/kind';
import { streams } from '../../lib/config';
import { formatClock } from '../../lib/format';
import type { TrackKind } from '../../lib/types';
import { app, player, playerState, serverNow } from '../../state';
import { Fader, LatchButton, RotarySwitch } from '../instruments';
import { Lamp } from '../primitives/Lamp';
import { Legend } from '../primitives/Legend';
import { Panel } from '../primitives/Panel';
import { Sticker } from '../primitives/Sticker';
import { armAnalyser, carrier, current, currentKind, debugPlaying, tuneState, tuneSub } from './console-state';
import { EYEBROW, artistLine, elapsedSec, titleOf } from './select';

/**
 * The title as a VFD: the real text is always in the accessible node; the visible glyphs
 * re-strike left to right when the track changes (not on first paint, not with reduced motion).
 */
export function VfdTitle({ text, kind, trackId }: { text: string; kind: TrackKind; trackId: string }) {
  const vis = useRef<HTMLSpanElement>(null);
  const seen = useRef<string | null>(null);
  useEffect(() => {
    const node = vis.current;
    if (!node) return;
    const animate = seen.current !== null && seen.current !== trackId && !loop.reduced;
    seen.current = trackId;
    if (!animate) {
      node.textContent = text || '—';
      return;
    }
    const s = new Scrambler();
    s.start(text, performance.now());
    const off = loop.add((_, now) => {
      const f = s.frame(now);
      if (f !== null) node.textContent = f;
      if (!s.running) off();
    });
    return () => {
      off();
      node.textContent = text || '—';
    };
  }, [text, trackId]);
  return (
    <h3 class="title phos" data-kind={kind}>
      <span class="sr">{text}</span>
      <span aria-hidden="true" ref={vis} />
    </h3>
  );
}

const QUALITY = streams.map((s) => ({ value: s.path, label: String(s.bitrate) }));

function Controls() {
  const snap = playerState.value;
  const state = tuneState.value;
  const kbps = snap?.stream.bitrate ?? 128;
  const press = () => {
    tuneSub.value = undefined;
    if (debugPlaying.value) {
      debugPlaying.value = false;
      return;
    }
    if (!player) return;
    if (state === 'idle' || state === 'error') armAnalyser();
    void player.toggle();
  };
  const hop = (path: string) => {
    if (!player) return;
    const on = state === 'playing' || state === 'loading';
    const next = streams.find((s) => s.path === path);
    if (on && next) tuneSub.value = `Hopping to ${next.bitrate}k`;
    void player.setStream(path);
  };
  const on = state === 'playing' || state === 'loading';
  return (
    <div class="strip">
      <LatchButton
        state={state}
        sub={debugPlaying.value ? 'Debug: no audio' : state === 'loading' ? tuneSub.value : undefined}
        note={on ? `stream ${kbps} kbps` : undefined}
        onPress={press}
      />
      <Fader
        value={Math.round((snap?.volume ?? 0.7) * 100)}
        disabled={snap ? !snap.volumeSupported : false}
        onInput={(v) => player?.setVolume(v / 100)}
      />
      <RotarySwitch
        legend="Feed kbps"
        tri={{ zh: '码率' }}
        name="feed"
        options={QUALITY}
        value={snap?.stream.path ?? '/radio-128'}
        onChange={hop}
      />
    </div>
  );
}

const KINDS: TrackKind[] = ['music', 'break', 'bumper'];

/** On-air programme: kind lamps, the VFD readout with progress, and the listening controls. */
export function OnAir() {
  const t = current.value;
  const kind = currentKind.value;
  const data = app.value.data;
  const car = carrier.value;
  const readout = useRef<HTMLDivElement>(null);
  const vfd = useRef<HTMLDivElement>(null);
  const prev = useRef<{ id: string | null; car: string }>({ id: null, car });

  // Readout luminance follows the power sequence (standby glow, strike-up, fade-down).
  useEffect(() => {
    if (debugPlaying.value) bus.power.lum = 1;
    let last = -1;
    return loop.add(() => {
      const lum = bus.power.lum;
      if (Math.abs(lum - last) > 0.002) {
        vfd.current?.style.setProperty('--lum', lum.toFixed(3));
        last = lum;
      }
      bus.pulse = Math.max(0, bus.pulse - 0.08);
    });
  }, []);

  // Glitch only as a state signal: a bulletin cutting in, or the carrier degrading.
  const id = t?.asset_id ?? null;
  useEffect(() => {
    const p = prev.current;
    const trackChanged = p.id !== null && id !== p.id;
    const degraded = p.car === 'live' && car !== 'live';
    prev.current = { id, car };
    if (trackChanged) bus.pulse = 1;
    if (!loop.reduced && ((trackChanged && kind === 'break') || degraded)) {
      const el = readout.current;
      if (!el) return;
      el.classList.remove('glitch');
      el.getBoundingClientRect(); // reflow so the animation restarts
      el.classList.add('glitch');
      const timer = window.setTimeout(() => el.classList.remove('glitch'), 650);
      return () => window.clearTimeout(timer);
    }
  }, [id, car, kind]);

  const state = tuneState.value;
  useEffect(() => {
    if (state === 'playing' || state === 'idle') tuneSub.value = undefined;
  }, [state]);

  const elapsed = elapsedSec(t, serverNow.value) ?? 0;
  const dur = t?.duration_sec ?? 0;
  const pct = dur > 0 ? Math.min(100, (elapsed / dur) * 100) : 0;
  const xf = data?.crossfade.music_sec ?? 0;
  return (
    <Panel name="prog" aria-labelledby="l-prog">
      <Legend en="On air" zh="播出" id="Siaran" ru="Эфир" htmlId="l-prog" note={`crossfade ${xf.toFixed(1)} s`} />
      <div class="kinds" aria-hidden="true">
        {KINDS.map((k) => (
          <span key={k} class={k === kind ? 'kind engr lit' : 'kind engr'}>
            <Lamp colour={KIND_LAMP[k]} on={k === kind} />
            {KIND_LABEL[k]}
          </span>
        ))}
      </div>
      <Sticker variant="asset" style={{ right: '26px', top: '14px' }}>
        <span>
          <i>TIANHE-KAIROS</i> 物流 LOGISTIK
        </span>
        <span>
          ASSET 0x4471-C · <i>资产 DO NOT REMOVE</i>
        </span>
      </Sticker>
      <div ref={readout} class={car === 'live' ? 'window scan readout' : 'window scan readout jam'} data-kind={kind}>
        <div class="vfd" ref={vfd}>
          {t ? (
            <>
              <div class="eyebrow">
                <span class="dim">{EYEBROW[kind]}</span>
                <span class="dim num">{dur > 0 ? `−${formatClock(Math.max(0, dur - elapsed))}` : ''}</span>
              </div>
              <VfdTitle text={titleOf(t)} kind={kind} trackId={t.asset_id} />
              <p class="artist phos">{kind === 'music' ? artistLine(t) : t.artist || KIND_LABEL[kind]}</p>
              <div
                class="bar"
                role="progressbar"
                aria-label="Track position"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(pct)}
              >
                <i style={{ width: `${pct.toFixed(2)}%` }} />
              </div>
              <div class="times phos num">
                <span data-testid="elapsed">{formatClock(Math.min(elapsed, dur || elapsed))}</span>
                <span>{dur > 0 ? formatClock(dur) : '—'}</span>
              </div>
            </>
          ) : (
            <div class="idle-msg">
              <div class="eyebrow">
                <span class="dim">{car === 'nosignal' ? 'Carrier lost' : 'Acquiring carrier'}</span>
              </div>
              <h3 class="title phos">{car === 'nosignal' ? 'No signal' : 'Standing by'}</h3>
              <p class="artist phos">
                {car === 'nosignal'
                  ? 'The feed went quiet. This panel keeps listening and relocks on its own.'
                  : 'Waiting for the transmitter to report what is on air.'}
              </p>
            </div>
          )}
        </div>
      </div>
      <Controls />
    </Panel>
  );
}
