import { expect, test, type Page } from '@playwright/test';

/** Console 2043 (?ui=console) against the production build, feed mocked, desktop + mobile projects. */

const payload = {
  updated_at: new Date().toISOString(),
  system_status: 'online',
  crossfade: { music_sec: 4, breaks_sec: 0 },
  stream: {
    source: [96, 128, 192].map((bitrate) => ({
      listenurl: bitrate === 192 ? '/radio' : `/radio-${bitrate}`,
      bitrate,
      listeners: 1,
      listener_peak: 5,
      samplerate: 44100,
      channels: 2,
      stream_start_iso8601: '2026-09-19T04:57:53+0000',
    })),
  },
  current: {
    asset_id: 'a',
    title: 'Smoke Test Song',
    artist: 'E2E',
    album: 'Unknown Album',
    duration_sec: 240,
    played_at: new Date(Date.now() - 60_000).toISOString(),
    source: 'music',
    kind: 'music',
  },
  breaks_queue: [{ asset_id: 'b', title: 'Station ID 0xE2E', artist: 'LBR', source: 'bumper', duration_sec: 6 }],
  music_queue: [{ asset_id: 'c', title: 'ЛИТАНИЯ 夜间 Next', artist: 'E2E', source: 'music', duration_sec: 200 }],
  history: [
    {
      asset_id: 'd',
      title: 'Previous <b>Song</b>',
      artist: 'E2E',
      source: 'music',
      played_at: new Date(Date.now() - 300_000).toISOString(),
    },
  ],
};

const breaks = Array.from({ length: 5 }, (_, i) => ({
  filename: `b${i}.mp3`,
  timestamp: `2026-09-22T${String(16 - i).padStart(2, '0')}:00:07`,
  url: `/api/breaks/b${i}.mp3`,
  size_bytes: 1_500_000,
}));

async function setup(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  await page.route('**/api/stream', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' },
      body: `data: ${JSON.stringify(payload)}\n\nevent: ping\ndata: {}\n\n`,
    }),
  );
  await page.route('**/api/breaks/index.json', (route) =>
    route.fulfill({ json: { generated_at: 'x', count: breaks.length, breaks } }),
  );
  // No real audio in CI: every stream request fails fast unless a test overrides play().
  await page.route(/\/radio(-\d+)?$/, (route) => route.abort());
  return errors;
}

test('console renders the live feed as text, without autoplay or errors', async ({ page }, info) => {
  const errors = await setup(page);
  await page.goto('/?ui=console');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/LAST BYTE RADIO/i);
  await expect(page.getByRole('heading', { level: 3, name: 'Smoke Test Song' })).toBeVisible();
  await expect(page.locator('.c-car [role="status"]')).toContainText(/Holding|Jammed|Acquiring/);
  await expect(page.getByText('Previous <b>Song</b>')).toBeVisible();
  await expect(page.getByText('ЛИТАНИЯ 夜间 Next')).toBeVisible();
  await expect(page.locator('main b', { hasText: 'Song' })).toHaveCount(0);
  await expect(page.getByTestId('elapsed')).toHaveText(/^1:0\d$/);
  await expect(page.getByRole('meter', { name: 'Position' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Tune in/ })).toHaveAttribute('aria-pressed', 'false');
  expect(await page.locator('audio[src]').count()).toBe(0);
  // The choice sticks: a plain visit keeps the console.
  await page.goto('/');
  await expect(page.locator('.rack.console')).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: info.outputPath('console.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('tune-in state machine: lock, refuse, retry, play, go dark', async ({ page }) => {
  await setup(page);
  await page.goto('/?ui=console');
  const tune = page.locator('button.tune');
  await expect(tune).toHaveAttribute('data-state', 'idle');
  await tune.click();
  // The stream is refused (aborted): the key says so and stays unlatched.
  await expect(tune).toHaveAttribute('data-state', 'error');
  await expect(tune).toContainText('No carrier');
  await expect(tune).toHaveAttribute('aria-pressed', 'false');

  // Now let playback "succeed".
  await page.evaluate(() => {
    HTMLMediaElement.prototype.play = function (this: HTMLMediaElement) {
      setTimeout(() => this.dispatchEvent(new Event('playing')), 50);
      return Promise.resolve();
    };
  });
  await page.unroute(/\/radio(-\d+)?$/);
  await page.route(/\/radio(-\d+)?$/, (route) => route.fulfill({ status: 204 }));
  await tune.click();
  await expect(tune).toHaveAttribute('data-state', 'playing');
  await expect(tune).toHaveAttribute('aria-pressed', 'true');
  await expect(tune).toContainText('On air');
  await expect(page.locator('.mcap').first()).toContainText(/program/);
  await tune.click();
  await expect(tune).toHaveAttribute('data-state', 'idle');
  await expect(tune).toContainText('Tune in');
});

test('rotary feed switch works from the keyboard and is remembered', async ({ page }) => {
  await setup(page);
  await page.goto('/?ui=console');
  const r128 = page.getByRole('radio', { name: '128' });
  await expect(r128).toBeChecked();
  await r128.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('radio', { name: '192' })).toBeChecked();
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowLeft');
  await expect(page.getByRole('radio', { name: '96' })).toBeChecked();
  await expect(page.locator('.band .legend b')).toHaveText('96k');
  expect(await page.evaluate(() => localStorage.getItem('radio.stream'))).toBe('/radio-96');
});

test('bulletins expand in place and the archive route lists every reel', async ({ page }) => {
  const errors = await setup(page);
  await page.goto('/?ui=console');
  const more = page.getByRole('button', { name: /Archive ▸ 2 more/ });
  await more.scrollIntoViewIfNeeded();
  await expect(more).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('12:00')).toBeHidden();
  await more.click();
  await expect(page.getByRole('button', { name: /Archive ▾ hide/ })).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('12:00')).toBeVisible();
  await page.getByRole('link', { name: 'Archive', exact: true }).click();
  await expect(page).toHaveURL(/\/archive$/);
  await expect(page.getByText('5 reels · last 24 h')).toBeVisible();
  await expect(page.locator('.tape')).toHaveCount(5);
  await page.getByRole('link', { name: /Live band/ }).click();
  await expect(page.getByRole('heading', { level: 3, name: 'Smoke Test Song' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('console is the default for new visitors and ?ui=classic opts out, remembered', async ({ page }) => {
  await setup(page);
  await page.goto('/');
  await expect(page.locator('.rack.console')).toBeVisible();
  await page.goto('/?ui=classic');
  await expect(page.getByRole('button', { name: 'TUNE IN' })).toBeVisible();
  await expect(page.locator('.rack')).toHaveCount(0);
  await page.goto('/');
  await expect(page.locator('.rack')).toHaveCount(0); // choice remembered
});
