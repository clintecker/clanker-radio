import { useEffect, useRef } from 'preact/hooks';
import { loop } from '../../engine/loop';
import { REKEY_MS, newKey, rekeyFrame } from '../../engine/scramble';
import { station } from '../../lib/config';
import { app, serverNow } from '../../state';
import { Lamp } from '../primitives/Lamp';
import { Tri } from '../primitives/Legend';
import { carrier, connection, current } from './console-state';
import { CARRIER_WORD, listenerCount, odometer } from './select';

const pad = (n: number) => String(n).padStart(2, '0');

/** Session key: re-keys (with a scramble) on every track change. Cosmetic, like the rest of the crypto. */
function SessionKey({ assetId }: { assetId: string }) {
  const el = useRef<HTMLSpanElement>(null);
  const keyAt = useRef(Date.now());
  const first = useRef(true);

  useEffect(() => {
    const key = newKey();
    keyAt.current = Date.now();
    const node = el.current;
    if (!node) return;
    if (first.current || loop.reduced) {
      first.current = false;
      node.textContent = key;
      return;
    }
    const t0 = performance.now();
    let last = 0;
    node.classList.add('rekey');
    const off = loop.add((_, now) => {
      const t = now - t0;
      if (t > REKEY_MS) {
        node.textContent = key;
        node.classList.remove('rekey');
        off();
        return;
      }
      if (now - last < 45) return;
      last = now;
      node.textContent = rekeyFrame(key, t);
    });
    return off;
  }, [assetId]);

  const age = Math.max(0, Math.floor((serverNow.value - keyAt.current) / 1000));
  return (
    <div class="cell c-key">
      <span class="k">Session key · {age < 60 ? `${age}s` : `${Math.floor(age / 60)}m`} old</span>
      <span class="v num" ref={el} aria-label="Session key, re-keys every track" />
      <Tri zh="密钥" id="Kunci" ru="Ключ" />
    </div>
  );
}

/** Brand plate + the four-cell status instrument: carrier, listeners, UTC clock, session key. */
export function StatusStrip() {
  const conn = connection.value;
  const car = carrier.value;
  const data = app.value.data;
  const listeners = listenerCount(data);
  const [lz, digits] = odometer(listeners);
  const d = new Date(serverNow.value);
  const colonsOn = d.getUTCMilliseconds() < 500;
  return (
    <header class="rail">
      <div class="brand">
        <h1 class="engr">{station.name}</h1>
        <p class="plate engr-2">
          2043 · unlicensed AI transmitter · Chicago exclusion zone <b>curfew 22:00 · stay off the grid</b>
        </p>
      </div>
      <div class="window status" role="group" aria-label="Station status">
        <div class="cell c-car" data-conn={car}>
          <span class="k">Carrier</span>
          <span class="v" role="status" aria-live="polite">
            <Lamp
              colour={car === 'live' ? 'cyan' : car === 'reconnecting' ? 'amber' : 'magenta'}
              on
              size="md"
              class="conn-lamp"
            />
            <span>{CARRIER_WORD[conn]}</span>
          </span>
          <Tri zh="信号" id="Sinyal" ru="Сигнал" />
        </div>
        <div class="cell c-lst">
          <span class="k">Listeners</span>
          <span class="v phos num" aria-label={`${listeners} listening`}>
            <span class="lz" aria-hidden="true">
              {lz}
            </span>
            <span aria-hidden="true">{digits}</span>
          </span>
          <Tri zh="收听" id="Pendengar" ru="Слушают" />
        </div>
        <div class="cell c-clk">
          <span class="k">Station clock · UTC</span>
          <span class="v phos num clock" role="timer" aria-label="Station time, UTC">
            {pad(d.getUTCHours())}
            <span class={colonsOn ? 'col' : 'col off'}>:</span>
            {pad(d.getUTCMinutes())}
            <span class={colonsOn ? 'col' : 'col off'}>:</span>
            {pad(d.getUTCSeconds())}
          </span>
          <Tri zh="时间" id="Waktu" ru="Время" />
        </div>
        <SessionKey assetId={current.value?.asset_id ?? ''} />
      </div>
    </header>
  );
}
