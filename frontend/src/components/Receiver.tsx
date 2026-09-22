import { streams } from '../lib/config';
import { formatUptime, normalizeIso } from '../lib/format';
import type { PlayerSnapshot } from '../lib/player';
import { app, player, playerState } from '../state';

const BUTTON_LABEL: Record<PlayerSnapshot['state'], string> = {
  idle: 'TUNE IN',
  loading: 'TUNING…',
  playing: 'TUNE OUT',
  error: 'RETRY',
};
const BUTTON_STYLE: Record<PlayerSnapshot['state'], string> = {
  idle: '',
  loading: 'text-phosphor-dim border-phosphor-dim',
  playing: 'bg-phosphor/15 shadow-[0_0_10px_rgba(127,255,127,.4)]',
  error: 'text-alarm border-alarm',
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      {label}: <span class="text-phosphor">{value}</span>
    </div>
  );
}

/** Transport controls plus the Icecast stats for the selected quality. No autoplay, ever. */
export function Receiver() {
  const snap = playerState.value;
  const p = player;
  if (!snap || !p) return null;
  const sources =
    app.value.data?.stream && 'source' in app.value.data.stream ? (app.value.data.stream.source ?? []) : [];
  const src = sources.find((s) => s.bitrate === snap.stream.bitrate) ?? sources[0] ?? null;
  const start = src?.stream_start_iso8601 ?? src?.stream_start;
  const on = snap.state === 'playing' || snap.state === 'loading';

  return (
    <section class="mb-10" aria-labelledby="controls-heading">
      <div class="eyebrow" id="controls-heading">
        RECEIVER
      </div>
      <div class="flex flex-wrap gap-y-4 gap-x-6 items-center mb-4">
        <button
          type="button"
          class={`btn-term max-sm:w-full ${BUTTON_STYLE[snap.state]}`}
          aria-pressed={on}
          onClick={() => void p.toggle()}
        >
          {BUTTON_LABEL[snap.state]}
        </button>
        {snap.volumeSupported && (
          <label class="flex items-center gap-2.5 text-[0.6rem] text-phosphor-dim tracking-[0.15em]">
            VOL
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(snap.volume * 100)}
              class="w-28"
              onInput={(e) => p.setVolume(Number(e.currentTarget.value) / 100)}
            />
          </label>
        )}
        <label class="flex items-center gap-2.5 text-[0.6rem] text-phosphor-dim tracking-[0.15em]">
          QUALITY
          <select
            class="bg-phosphor-faint border border-phosphor/30 text-phosphor text-[0.65rem] px-2 py-1 cursor-pointer"
            value={snap.stream.path}
            onChange={(e) => void p.setStream(e.currentTarget.value)}
          >
            {streams.map((s) => (
              <option key={s.path} value={s.path}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div class="flex flex-wrap gap-y-2 gap-x-5 text-[0.65rem] text-phosphor-dim tabular-nums">
        <Stat label="LISTENERS" value={src ? String(src.listeners) : '—'} />
        <Stat label="BITRATE" value={src ? `${src.bitrate} kbps` : '—'} />
        <Stat label="SAMPLE RATE" value={src ? `${(src.samplerate / 1000).toFixed(1)} kHz` : '—'} />
        <Stat label="UPTIME" value={formatUptime(start ? normalizeIso(start) : undefined)} />
      </div>
      {snap.state === 'error' && (
        <p class="text-[0.7rem] text-alarm mt-2" role="alert">
          Stream would not start. Check your connection and press RETRY.
        </p>
      )}
    </section>
  );
}
