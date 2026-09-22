import preact from '@preact/preset-vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

// Build-time branding defaults. Override in frontend/.env.local (gitignored) or the
// shell, e.g. VITE_STATION_NAME="WKRP COCONUT ISLAND" npm run build.
const BRANDING_DEFAULTS: Record<string, string> = {
  VITE_STATION_NAME: 'LAST BYTE RADIO',
  VITE_STATION_TAGLINE: 'CHICAGO WASTELAND // ENCRYPTED BROADCAST',
  VITE_PLAYLIST_URL: '/stream.m3u',
  VITE_SITE_URL: 'https://radio.clintecker.com',
};
for (const [key, value] of Object.entries(BRANDING_DEFAULTS)) process.env[key] ??= value;

const buildStamp = `${new Date().toISOString().slice(0, 16).replace('T', ' ')}Z`;
const LIVE = 'https://radio.clintecker.com';
const proxy = Object.fromEntries(
  ['/api', '/radio', '/radio-128', '/radio-96', '/stream.m3u'].map((p) => [p, { target: LIVE, changeOrigin: true }]),
);

export default defineConfig({
  plugins: [preact(), tailwindcss()],
  base: '/',
  define: { __BUILD_STAMP__: JSON.stringify(buildStamp) },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: true, target: 'es2022' },
  server: { proxy },
  preview: { proxy },
  test: {
    environment: 'jsdom',
    globals: true, // lets @testing-library auto-cleanup between tests
    include: ['src/**/*.test.{ts,tsx}'],
    setupFiles: ['src/test-setup.ts'],
  },
});
