import { KIND_LABEL, KIND_LAMP } from '../../design/kind';
import { formatTimeAgo } from '../../lib/format';
import type { Track } from '../../lib/types';
import { app, serverNow } from '../../state';
import { Lamp } from '../primitives/Lamp';
import { Legend } from '../primitives/Legend';
import { Panel } from '../primitives/Panel';
import { Sticker } from '../primitives/Sticker';
import { durationLabel, queueOf, titleOf, trackKind } from './select';

/** One log/queue line: kind lamp, title (as text), artist or kind, and a right-hand figure. */
export function TrackRow({ t, right, up }: { t: Track; right: string; up?: boolean }) {
  const k = trackKind(t);
  return (
    <li class={up ? 'row up' : 'row'} data-kind={k}>
      <Lamp colour={KIND_LAMP[k]} on size="sm" />
      <div>
        <div class="t">{titleOf(t)}</div>
        <div class="a">{k === 'music' ? t.artist || 'Unknown artist' : KIND_LABEL[k]}</div>
      </div>
      <div class="d num">{right}</div>
    </li>
  );
}

export function NextUp() {
  const q = queueOf(app.value.data);
  const hasData = app.value.data !== null;
  return (
    <Panel name="next" aria-labelledby="l-next">
      <Legend
        en="Next up"
        zh="下一首"
        id="Berikut"
        ru="Далее"
        htmlId="l-next"
        note={hasData ? <span class="num">{q.total} queued</span> : null}
      />
      <div class="window fill">
        {q.cutIns.length > 0 && (
          <>
            <div class="subhead">Cut in before the next song</div>
            <ul class="list">
              {q.cutIns.map((t, i) => (
                <TrackRow key={`${t.asset_id}-${i}`} t={t} right={durationLabel(t)} up={i === 0} />
              ))}
            </ul>
          </>
        )}
        <div class="subhead">{q.cutIns.length ? 'Then' : 'Up next'}</div>
        <ul class="list">
          {q.music.length === 0 && (
            <li class="empty">
              {hasData ? 'Queue dry. The station picks the next record itself.' : 'Waiting for the running order.'}
            </li>
          )}
          {q.music.map((t, i) => (
            <TrackRow key={`${t.asset_id}-${i}`} t={t} right={durationLabel(t)} up={!q.cutIns.length && i === 0} />
          ))}
        </ul>
      </div>
    </Panel>
  );
}

export function Log() {
  const history = app.value.data?.history ?? [];
  const now = new Date(serverNow.value);
  return (
    <Panel name="log" aria-labelledby="l-log">
      <Sticker variant="cyr" style={{ right: '40px', bottom: '-6px' }}>
        ЭФИР НЕ ПРЕРЫВАТЬ
      </Sticker>
      <Legend
        en="Log"
        zh="记录"
        id="Catatan"
        ru="Журнал"
        htmlId="l-log"
        note={history.length ? `last ${history.length} plays` : null}
      />
      <div class="window fill">
        <ul class="list">
          {history.length === 0 && <li class="empty">Log wiped. Nothing aired since the last restart.</li>}
          {history.map((t, i) => (
            <TrackRow
              key={`${t.asset_id}-${t.played_at ?? i}`}
              t={t}
              right={t.played_at ? formatTimeAgo(new Date(t.played_at), now) : ''}
            />
          ))}
        </ul>
      </div>
    </Panel>
  );
}
