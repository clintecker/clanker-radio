/** Station branding and stream endpoints. Override at build time with VITE_* env vars. */

export interface StreamOption {
  path: string;
  bitrate: number;
  label: string;
}

const env = import.meta.env;

export const station = {
  name: env.VITE_STATION_NAME ?? 'LAST BYTE RADIO',
  tagline: env.VITE_STATION_TAGLINE ?? 'CHICAGO WASTELAND // ENCRYPTED BROADCAST',
  sseUrl: env.VITE_SSE_URL ?? '/api/stream',
  playlistUrl: env.VITE_PLAYLIST_URL ?? '/stream.m3u',
} as const;

export const streams: readonly StreamOption[] = [
  { path: '/radio-96', bitrate: 96, label: '96 kbps' },
  { path: '/radio-128', bitrate: 128, label: '128 kbps' },
  { path: '/radio', bitrate: 192, label: '192 kbps' },
];

export const defaultStream: StreamOption = streams[1] ?? { path: '/radio-128', bitrate: 128, label: '128 kbps' };

/** Consider the feed stale if no SSE message (data or keepalive) arrives within this window. */
export const STALE_AFTER_MS = 75_000; // push_daemon keepalive is every 30s

/**
 * The stream endpoints send exactly one `Access-Control-Allow-Origin: *`, so the <audio>
 * element can be CORS-mode and Web Audio can read real samples (VU, band watch). If that
 * ever regresses, set false: playback keeps working and the meters fall back to the
 * simulated program signal.
 */
export const STREAM_CORS_OK = true;
