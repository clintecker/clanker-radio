# Console 2043: production frontend build plan

**Goal:** Ship the approved "Console 2043" prototype (`docs/design/console-2043-prototype.html`,
published at https://claude.ai/artifact/RXTHaWpPWLxFeo7kguwwwy) as the production web
player in `frontend/`, rebuilt as typed Preact components on the live feed, at the same
visual quality, with no regression in the hardening already shipped.

**Stack (unchanged):** Preact + @preact/signals, Vite, TypeScript strict, Tailwind v4,
Vitest + Testing Library, Playwright. The tested `src/lib/` modules (feed + watchdog,
clock sync, payload validation, player, archive) are kept as-is and become the data layer.

---

## 1. Architecture

```
src/
  lib/                 data + domain (exists, unchanged API)
  state.ts             signals: app, now, serverNow, playerState  (exists)
  engine/              NEW: frame loop + physics, framework-free, unit-tested
    loop.ts            one rAF loop; subscribers; pauses on visibilitychange
    spring.ts          critically-damped spring w/ overshoot + end-stop bounce
    lamp.ts            incandescent warm-up/cool-down envelope
    vu.ts              VU ballistics (300 ms integration) + simulated program signal
    scramble.ts        split-flap/VFD title resolve
  design/              NEW: design system
    tokens.css         @theme tokens (color, type, space, radii, shadows, motion)
    materials.css      faceplate, bevel, recess, glass, screws, hazard, stickers
    textures.ts        generate hammertone/grime/rain once -> data-URI, cache in sessionStorage
  components/
    primitives/        Panel, Screw, Lamp, Legend (trilingual), Readout (VFD glass), Sticker
    instruments/       Meter (generic), VuMeter, PositionMeter, CarrierMeter,
                       Fader, RotarySwitch, LatchButton (TUNE IN), BandWatch (canvas)
    modules/           StatusStrip, OnAir, NextUp, Log, Bulletins, MeterBay, BandWatchBay
  pages/               Live (composes modules), Archive (full list, reuses Bulletins row)
  app.tsx              shell + router (exists)
```

**Rules**
- Components never own timing. Anything that animates registers with `engine/loop`
  and writes through refs/CSS custom properties, so Preact re-renders stay at
  data frequency (feed pushes + 4 Hz clock), never 60 Hz.
- Physics state lives in the engine; components pass targets (`needle.target = 0.62`).
- All feed text rendered as text (ESLint `innerHTML` ban stays).
- Debug controls (`?debug=1`, `?playing=1`, `?kind=`, `?conn=`, `?vw=`) move into a
  `DebugPanel` that is tree-shaken out of production builds via `import.meta.env.DEV`
  plus a `VITE_ENABLE_DEBUG` flag for staging.

## 2. CSS strategy (best-in-class, no framework fights)

- **Tailwind v4 for layout and spacing only;** materials and instruments are authored CSS
  in `@layer components`, because bevels, glass and printed meter faces are not
  utility-shaped. Cascade layers: `reset, tokens, base, materials, components, utilities`.
- **Design tokens as custom properties** in `@theme`: faceplate `#23282D`, well `#05070A`,
  legend `#C9D2D6/#7E8A90`, accents by content type (music amber `#FFB347`, bulletin magenta
  `#FF2E88`, ID/system cyan `#3EF2E0`), hazard `#E8C21A`, meter face `#D5E6E0`.
  Kind colour is set once per subtree with `data-kind` → `--kind` so every child
  (lamp, readout, list dot) inherits it; no per-component colour logic.
- **Lighting as tokens:** one key light (top-left) encoded as shadow tokens
  (`--bevel-hi`, `--bevel-lo`, `--recess`, `--cast`) so every module is lit consistently.
- **Container queries** (`@container`) for every module: modules lay out by their own
  width, not the viewport, so the same component works in a 3-column rack at 1440,
  2 columns at 1000 and stacked at 390. Viewport media queries only for the page grid.
- **Page grid:** CSS Grid with named areas (`status band onair next meters log bulletins`)
  and `grid-template-areas` per breakpoint; `subgrid` for the meter bay so all three
  headers/faces share rows (fixes the header alignment class of bug structurally).
- **Fluid type:** `clamp()` scale with a fixed step ratio; `text-wrap: balance` on titles,
  `font-variant-numeric: tabular-nums` on every readout, `font-feature-settings` for
  slashed zero in Martian Mono.
- **Fonts:** self-host subsetted WOFF2 (Big Shoulders Stencil/Display, Chakra Petch,
  Martian Mono; Noto Sans SC via `unicode-range` subset of the legend glyphs only),
  `font-display: swap`, metric-matched fallbacks with `size-adjust` to avoid CLS,
  preload the two faces above the fold. Removes the Google Fonts CSP exception.
- **Layout stability:** fixed intrinsic sizes on instruments (`aspect-ratio`, explicit
  well sizes); press/travel via `transform` + `box-shadow` only; `contain: layout paint`
  on each module; CLS target 0.
- **Motion:** `prefers-reduced-motion` handled centrally in `engine/loop` (springs snap,
  lamps step) plus a CSS guard; `@starting-style` for enter transitions; View Transitions
  API for Live ⇄ Archive route changes where supported.
- **Textures:** generated once on a canvas to data-URIs (cached), applied as
  `background-image`; no large images shipped.
- **Accessibility:** meters get `role="meter"` with `aria-valuenow`/`valuetext`;
  TUNE IN is `aria-pressed`; RotarySwitch is a radiogroup with arrow keys;
  Fader is a native range; all 44px targets; `:focus-visible` rings tuned per material;
  contrast checked for every token pair; trilingual legends `lang="zh"`/`id`/`ru`.

## 3. Build order (each step ships green: check + e2e + deploy)

1. **Design system foundation.** tokens.css, materials.css, textures.ts, fonts self-hosted,
   primitives (Panel, Screw, Lamp, Legend, Readout, Sticker) + a `/__kit` dev-only page
   rendering every primitive and state. Tests: token contrast script, Readout text escaping.
2. **Engine.** loop, spring, lamp, vu, scramble with unit tests (spring settles, overshoot
   bounded, reduced-motion snaps, loop pauses when hidden, VU ballistics timing).
3. **Instruments.** Meter (generic SVG face from a scale spec), then Vu/Position/Carrier;
   LatchButton with power-up sequence; Fader; RotarySwitch. Each in `/__kit` with states.
4. **Modules on live data.** StatusStrip, OnAir (title scramble on track change, kind
   lamps), NextUp, Log, compact Bulletins + Archive page, MeterBay (subgrid).
5. **BandWatch.** Canvas spectrum + waterfall on the engine loop at ~20 fps; carriers at
   96/128/192 from Icecast sources; jammer sweep on `reconnecting`, noise on `stale`;
   OffscreenCanvas when available.
6. **Page composition + responsive pass** at 1440/1000/390, header strip 2×2 on phone.
7. **Server fix for real VU:** remove the duplicated `Access-Control-Allow-Origin` on the
   stream (nginx + Icecast both add it). Then `crossOrigin="anonymous"` + AnalyserNode
   drives VuMeter and BandWatch from real audio, with the simulated signal as fallback.
8. **Hardening + perf:** Lighthouse ≥ 95 perf/a11y, CLS 0, main-thread idle while not
   playing, bundle budget (JS ≤ 45 kB gz, CSS ≤ 20 kB gz, fonts ≤ 120 kB), CSP updated.

## 4. Testing

- **Unit (Vitest):** engine math, scale specs (tick/label positions never collide),
  kind→token mapping, payload → view-model selectors.
- **Component (Testing Library):** every module against fixture payloads including long,
  CJK/Cyrillic and `<b>`-containing titles; empty/error states in operator voice.
- **Visual regression (Playwright `toHaveScreenshot`)** of `/__kit` and the Live page at
  1440/1000/390 with a frozen clock and mocked feed, per kind and connection state.
- **E2E:** tune-in state machine, rotary keyboard control, archive expand, route change,
  no console errors, axe-core a11y scan.

## 5. Risks / decisions

- **CJK font weight:** subset to the legend glyphs at build time (script extracts used
  characters from components) so Noto Sans SC stays under ~20 kB.
- **Canvas cost on low-end phones:** BandWatch drops to 10 fps and a single-row spectrum
  below a device-memory / battery-saver heuristic; pauses when off-screen
  (IntersectionObserver).
- **Rollback:** current Preact player stays deployable; new UI behind `?ui=console` until
  step 6 passes, then becomes default.

**Estimate:** steps 1-3 ~2 days, 4-6 ~2 days, 7-8 ~1 day.
