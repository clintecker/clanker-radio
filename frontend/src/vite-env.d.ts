/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_STATION_NAME?: string;
  readonly VITE_STATION_TAGLINE?: string;
  readonly VITE_SSE_URL?: string;
  readonly VITE_PLAYLIST_URL?: string;
  readonly VITE_SITE_URL?: string;
  readonly VITE_ENABLE_DEBUG?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
declare const __BUILD_STAMP__: string;
