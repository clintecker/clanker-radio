import { expect, test, type Page } from '@playwright/test';

const payload = {
  updated_at: new Date().toISOString(),
  system_status: 'online',
  crossfade: { music_sec: 4, breaks_sec: 0 },
  stream: {
    source: [
      {
        listenurl: '/radio-128',
        bitrate: 128,
        listeners: 2,
        listener_peak: 5,
        samplerate: 44100,
        channels: 2,
        stream_start_iso8601: '2026-09-19T04:57:53+0000',
      },
    ],
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
  music_queue: [{ asset_id: 'c', title: 'Next Song', artist: 'E2E', source: 'music', duration_sec: 200 }],
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

/** Serve one SSE message then hold the connection open long enough for the test. */
async function mockFeed(page: Page) {
  await page.route('**/api/stream', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' },
      body: `data: ${JSON.stringify(payload)}\n\nevent: ping\ndata: {}\n\n`,
    }),
  );
  await page.route('**/api/breaks/index.json', (route) =>
    route.fulfill({
      json: {
        generated_at: 'x',
        count: 1,
        breaks: [
          { filename: 'b.mp3', timestamp: '2026-09-22T11:07:47', url: '/api/breaks/b.mp3', size_bytes: 1_500_000 },
        ],
      },
    }),
  );
}

test.beforeEach(async ({ page }) => mockFeed(page));

test('live page shows the feed, escapes titles, and does not autoplay', async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 2 })).toHaveText('Smoke Test Song');
  await expect(page.getByRole('status')).toContainText(/LIVE|RECONNECTING/);
  await expect(page.getByText('Station ID 0xE2E')).toBeVisible();
  await expect(page.getByText('↳ then Next Song')).toBeVisible();
  await expect(page.getByText('Previous <b>Song</b>')).toBeVisible();
  expect(await page.locator('main b').count()).toBe(0);
  await expect(page.getByTestId('elapsed')).toHaveText(/^1:0\d$/);
  await expect(page.getByRole('button', { name: 'TUNE IN' })).toHaveAttribute('aria-pressed', 'false');
  expect(await page.locator('audio[src]').count()).toBe(0);
  expect(errors).toEqual([]);
  await page.waitForTimeout(300);
  await page.screenshot({ path: testInfo.outputPath('live.png'), fullPage: true });
});

test('archive route lists bulletins and deep-links', async ({ page }, testInfo) => {
  await page.goto('/archive');
  await expect(page.getByText('BULLETIN ARCHIVE', { exact: false })).toBeVisible();
  await expect(page.getByText(/Sep 22, 11:07/)).toBeVisible();
  await page.getByRole('link', { name: 'LIVE' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { level: 2 })).toHaveText('Smoke Test Song');
  await page.screenshot({ path: testInfo.outputPath('archive.png'), fullPage: true });
});

test('has rich preview metadata and security-relevant headers in markup', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', /og-image\.png$/);
  await expect(page.locator('link[rel="manifest"]')).toHaveCount(1);
  await expect(page.locator('script:not([type="module"])')).toHaveCount(0);
});
