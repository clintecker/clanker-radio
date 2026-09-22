# Web player

The station's public page: now playing, next up, recent transmissions, and the
live stream receiver. Vite + TypeScript, no framework, no runtime dependencies.

```
npm install
npm run dev        # http://localhost:5173, /api and /radio* proxied to the live station
npm test           # vitest unit tests (format, clock sync)
npm run build      # dist/ = what nginx serves from /srv/ai_radio/public
```

From the repo root: `make frontend-dev`, `make frontend-test`, `make deploy-frontend`.

## Branding

Build-time. Defaults live in `vite.config.ts`; override in `.env.local` (gitignored) or the shell:
`VITE_STATION_NAME`, `VITE_STATION_TAGLINE`, `VITE_PLAYLIST_URL`, `VITE_SSE_URL`.

## How it works

- `lib/sse.ts` holds one `EventSource` to `/api/stream`. The browser reconnects on
  its own; a watchdog marks the feed **NO SIGNAL** if neither data nor the daemon's
  `ping` event arrives for 75s and forces a fresh connection. The badge says LIVE
  only while the feed is actually flowing.
- `lib/clock.ts` estimates the server clock offset from live pushes so the
  progress bar tracks the server, not the visitor's clock. The replayed state a
  client receives on connect is excluded because its timestamp is stale.
- `lib/player.ts` wraps the `<audio>` element. No autoplay: nothing is fetched
  and no Icecast listener is counted until TUNE IN. Stopping drops the connection.
  Volume is hidden on iOS, where Safari ignores it.
- `ui/crossfade.ts` mirrors Liquidsoap's crossfade visually. Inside the window
  it shows an INCOMING strip and glitches out a frozen clone of the current
  card; the card's own text only changes when the feed confirms the new track,
  so a late-inserted break never shows the wrong title as "now".
- `ui/signal.ts` is the spectrum strip under the progress bar, driven by a Web
  Audio analyser on the stream while tuned in, and a faint noise floor otherwise.
- All station data is written with `textContent` through `ui/dom.ts`; nothing
  from the feed is ever set as HTML.
