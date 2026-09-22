import { Bulletins, Log, MeterBay, NextUp, OnAir, ServicePanel } from '../../components/modules';
import { ConsoleShell } from './ConsoleShell';

/** Console 2043 live page. */
export function ConsoleLive() {
  return (
    <ConsoleShell>
      <main class="grid-live">
        <OnAir />
        <MeterBay />
        <NextUp />
        <Log />
        <Bulletins />
        <ServicePanel />
      </main>
    </ConsoleShell>
  );
}
