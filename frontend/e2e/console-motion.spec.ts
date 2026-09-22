import { expect, test } from '@playwright/test';

/** Regression: frame-loop writes must actually animate (a NaN guard once blocked every write). */
test('console knob springs through intermediate angles when the feed changes', async ({ page }) => {
  await page.route('**/api/stream', (route) =>
    route.fulfill({ status: 200, headers: { 'content-type': 'text/event-stream' }, body: '' }),
  );
  await page.goto('/?ui=console');
  const knob = page.locator('.knob');
  await expect(knob).toBeVisible();
  const angles = await knob.evaluate(
    (k: HTMLElement) =>
      new Promise<number[]>((resolve) => {
        const out: number[] = [];
        k.click();
        const read = () => {
          out.push(parseFloat(/rotate\(([-\d.]+)deg\)/.exec(k.style.transform)?.[1] ?? 'NaN'));
          if (out.length < 30) requestAnimationFrame(read);
          else resolve(out);
        };
        requestAnimationFrame(read);
      }),
  );
  const distinct = new Set(angles.map((a) => a.toFixed(0)));
  expect(distinct.size, `angles seen: ${angles.join(', ')}`).toBeGreaterThan(4);
  expect(Math.max(...angles)).toBeGreaterThan(52); // overshoots the detent before settling
});
