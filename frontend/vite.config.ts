import { defineConfig } from 'vitest/config';

// Build-time branding defaults. Override in frontend/.env.local (gitignored) or the
// shell, e.g. VITE_STATION_NAME="WKRP COCONUT ISLAND" npm run build.
const BRANDING_DEFAULTS: Record<string, string> = {
  VITE_STATION_NAME: 'LAST BYTE RADIO',
  VITE_STATION_TAGLINE: 'CHICAGO WASTELAND // ENCRYPTED BROADCAST',
  VITE_PLAYLIST_URL: '/stream.m3u',
};
for (const [key, value] of Object.entries(BRANDING_DEFAULTS)) process.env[key] ??= value;

export default defineConfig({
  // Served from the nginx root, so assets resolve relative to /
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    target: 'es2022',
  },
  server: {
    // Local dev against the live station: SSE + audio proxied to production
    proxy: {
      '/api': { target: 'https://radio.clintecker.com', changeOrigin: true },
      '/radio': { target: 'https://radio.clintecker.com', changeOrigin: true },
      '/radio-128': { target: 'https://radio.clintecker.com', changeOrigin: true },
      '/radio-96': { target: 'https://radio.clintecker.com', changeOrigin: true },
      '/stream.m3u': { target: 'https://radio.clintecker.com', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
  },
});
