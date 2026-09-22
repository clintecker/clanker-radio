import { Ear } from '../../components/primitives';
import { station } from '../../lib/config';

/** Console 2043 live page. Assembled module by module over the build steps. */
export function ConsoleLive() {
  return (
    <div class="rack console">
      <Ear side="l" />
      <Ear side="r" />
      <div class="rack-inner">
        <h1 class="engr">{station.name}</h1>
      </div>
    </div>
  );
}
