#!/usr/bin/env node
/**
 * Self-hosted console fonts. Copies the WOFF2 subsets we use out of @fontsource into
 * public/fonts, and cuts Noto Sans SC down to the Han glyphs that actually appear in
 * src/ (the trilingual legends), so CJK costs a few kB instead of 1.2 MB.
 *
 * Run after changing a legend: `npm run fonts` (needs `pyftsubset`, i.e. pip install fonttools brotli).
 * The output is committed, so a normal build never needs Python.
 */
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const out = join(root, 'public/fonts');
const fs = (pkg, file) => join(root, 'node_modules/@fontsource', pkg, 'files', file);
mkdirSync(out, { recursive: true });

const COPY = [
  ['big-shoulders-stencil-display', ['latin', 'latin-ext'], [800, 900]],
  ['big-shoulders-display', ['latin', 'latin-ext'], [800]],
  ['chakra-petch', ['latin', 'latin-ext'], [400, 500, 600]],
  ['martian-mono', ['latin', 'cyrillic'], [400, 500, 600]],
  ['noto-sans-sc', ['cyrillic'], [700]],
];
for (const [pkg, subsets, weights] of COPY) {
  for (const s of subsets)
    for (const w of weights) {
      const f = `${pkg}-${s}-${w}-normal.woff2`;
      copyFileSync(fs(pkg, f), join(out, f));
    }
}

// Han glyphs used anywhere in the source.
const han = new Set();
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(tsx?|css)$/.test(name)) for (const ch of readFileSync(p, 'utf8').match(/\p{Script=Han}/gu) ?? []) han.add(ch);
  }
};
walk(join(root, 'src'));
const text = [...han].sort().join('');
writeFileSync(join(out, 'noto-sans-sc-legend.txt'), text + '\n');
execFileSync('pyftsubset', [
  fs('noto-sans-sc', 'noto-sans-sc-chinese-simplified-700-normal.woff2'),
  `--text=${text}`,
  '--flavor=woff2',
  '--layout-features=*',
  `--output-file=${join(out, 'noto-sans-sc-legend-700.woff2')}`,
]);
console.log(`fonts: ${han.size} Han glyphs subset`);
