# Web player

The station's public page: now playing, next up, recent transmissions, the live
stream receiver, and a bulletin archive. Preact + signals, Tailwind v4, Vite,
TypeScript. ~19 kB of JavaScript gzipped.

```
npm install
npm run dev        # http://localhost:5173, /api and /radio* proxied to the live station
npm run check      # typecheck + lint + format check + unit tests
npm run e2e        # Playwright smoke tests against the production build (first: npm run e2e:install)
npm run build      # dist/ = what nginx serves from /srv/ai_radio/public
```

From the repo root: `make frontend-dev`, `make frontend-test`, `make deploy-frontend`.

## Layout

```
src/lib/        framework-free, unit-tested: sse (feed + watchdog), clock (server offset),
                payload (runtime validation), player (<audio>, no autoplay), archive, format
src/state.ts    signals that bridge lib/ into the UI: app (feed state), now (4 Hz clock),
                serverNow, playerState
src/components  NowPlaying (hero + crossfade), Signal (spectrum canvas), StatusBadge,
                Receiver (controls + Icecast stats), TrackList (Queue, History)
src/pages       Live (/), Archive (/archive)
src/app.tsx     shell: header, nav, router (preact-iso), footer with build stamp
src/styles      app.css: Tailwind theme tokens + the few custom keyframes
e2e/            Playwright smoke: mocked feed, desktop + mobile
```

## Branding

Build-time. Defaults live in `vite.config.ts`; override in `.env.local` (gitignored) or the shell:
`VITE_STATION_NAME`, `VITE_STATION_TAGLINE`, `VITE_PLAYLIST_URL`, `VITE_SSE_URL`, `VITE_SITE_URL`.
Colours and type are Tailwind theme tokens at the top of `src/styles/app.css`.

## Behaviour worth knowing

- The badge says LIVE only while the feed is flowing. A watchdog marks it NO SIGNAL if
  neither data nor the daemon's `ping` event arrives for 75s and reconnects with backoff.
- The progress bar runs on a server clock offset estimated from live pushes; the replayed
  state on connect is excluded because its timestamp is stale.
- No autoplay: nothing is fetched and no Icecast listener is counted until TUNE IN.
- The crossfade never shows an unconfirmed track as "now": an INCOMING strip names the
  queued track, and the old card glitches out only once the feed confirms the change.
- Every feed payload is validated at runtime; a bad message is dropped and the last good
  state stays on screen. All feed text is rendered as text, and ESLint forbids `innerHTML`.
- `/archive` lists the last 24h of bulletins from `/api/breaks/index.json` (served read-only
  by nginx) and only accepts URLs under that endpoint.
