import { BulletinList, useArchive } from '../../components/modules';
import { Legend } from '../../components/primitives/Legend';
import { Panel } from '../../components/primitives/Panel';
import { ConsoleShell } from './ConsoleShell';

/** Every bulletin of the last day, on the same reel rows as the live module. */
export function ConsoleArchive() {
  const load = useArchive();
  const n = load.kind === 'ready' ? load.index.breaks.length : null;
  return (
    <ConsoleShell>
      <main class="grid-archive">
        <Panel name="arch" aria-labelledby="l-archive">
          <Legend
            en="Bulletin archive"
            zh="新闻"
            id="Arsip"
            ru="Архив"
            htmlId="l-archive"
            note={n === null ? 'last 24 h' : `${n} reels · last 24 h`}
          />
          <div class="window fill">
            <BulletinList load={load} />
          </div>
          <div class="keys">
            <a class="key" href="/">
              ◂ Live band
            </a>
          </div>
        </Panel>
      </main>
    </ConsoleShell>
  );
}
