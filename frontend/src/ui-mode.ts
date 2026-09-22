/**
 * Which face the station wears. The classic player stays the default until the
 * Console 2043 build passes its rollout checks; `?ui=console` opts in (and
 * `?ui=classic` opts back out), remembered per browser.
 */
export type UiMode = 'classic' | 'console';

const KEY = 'radio.ui';

interface KV {
  getItem(k: string): string | null;
  setItem(k: string, v: string): void;
}

function storage(): KV | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function resolveUiMode(search: string, store: KV | null = storage()): UiMode {
  const asked = new URLSearchParams(search).get('ui');
  if (asked === 'console' || asked === 'classic') {
    try {
      store?.setItem(KEY, asked);
    } catch {
      /* private mode: choice lasts for this page only */
    }
    return asked;
  }
  try {
    return store?.getItem(KEY) === 'console' ? 'console' : 'classic';
  } catch {
    return 'classic';
  }
}
