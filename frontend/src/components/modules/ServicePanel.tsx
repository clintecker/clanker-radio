import { DEBUG_ENABLED } from '../../debug';
import { station } from '../../lib/config';
import { app, serverNow } from '../../state';
import { Legend } from '../primitives/Legend';
import { Panel } from '../primitives/Panel';
import { carrier, connOverride, debug } from './console-state';
import { carrierUptime, feedRates, listenerCount, listenerPeak } from './select';

/** Icecast figures and the station's own small print. */
export function ServicePanel() {
  const data = app.value.data;
  const car = carrier.value;
  const peak = Math.max(listenerPeak(data), listenerCount(data));
  const system = car === 'live' ? (data?.system_status ?? 'online') : car === 'reconnecting' ? 'jammed' : 'dark';
  const showDebug = DEBUG_ENABLED && debug.value.panel;
  const drop = () => {
    if (connOverride.value === null) connOverride.value = 'reconnecting';
    else if (connOverride.value === 'reconnecting') connOverride.value = 'stale';
    else connOverride.value = null;
  };
  return (
    <Panel name="svc" aria-labelledby="l-svc">
      <Legend en="Service panel" zh="维修" htmlId="l-svc" note="icecast" />
      <div class="stats">
        <div class="window stat">
          <b class="phos num">{carrierUptime(data, serverNow.value)}</b>
          <span>Carrier up</span>
        </div>
        <div class="window stat">
          <b class="phos num">{feedRates(data)}</b>
          <span>Feeds kbps</span>
        </div>
        <div class="window stat">
          <b class="phos num">{data ? String(peak) : '—'}</b>
          <span>Peak listeners</span>
        </div>
        <div class="window stat">
          <b class="phos">{system}</b>
          <span>System</span>
        </div>
      </div>
      <div class="keys">
        <a class="key" href={station.playlistUrl} download>
          Save .m3u
        </a>
        <a class="key" href="/archive">
          Archive
        </a>
        {showDebug && (
          <button class="key warn" type="button" onClick={drop}>
            {connOverride.value === null
              ? 'Drop signal'
              : connOverride.value === 'reconnecting'
                ? 'Kill carrier'
                : 'Restore'}
          </button>
        )}
      </div>
      <p class="foot">
        No licence, no owner. The station picks its own records and writes its own news. If this panel is lit, it is on
        air. Rig parts out of Huaqiangbei, Glodok and the Vladivostok container yards.
      </p>
      {showDebug && (
        <p class="foot">
          Debug: <code>?playing=1</code> <code>?kind=break|bumper</code> <code>?conn=reconnecting|dead</code>{' '}
          <code>?vw=390</code>. Drop signal only jams this page.
        </p>
      )}
    </Panel>
  );
}
