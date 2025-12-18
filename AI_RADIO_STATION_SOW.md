# AI Radio Station MVP — Request for Proposal & Statement of Work

## 1. Summary

We are commissioning a **single Ubuntu VM** "AI radio station" that:

* Streams **24/7 to Icecast** from an existing music library (~1,000+ tracks)
* Inserts **hourly spoken news + weather breaks** generated via LLM + TTS
* **Never goes dead air**, even if content generation fails
* Requires **minimal ongoing maintenance**

This is a personal/art project (not commercial broadcast).

---

## 2. Objectives

### Primary

1. Continuous, stable Icecast stream at all times.
2. Hourly break insertion (top-of-hour) using pre-rendered audio.
3. Robust failure behavior with multi-level fallbacks.

### Secondary

1. Simple operator overrides (drop-in "play next", force break, kill switch for AI generation).
2. Minimal, useful observability (logs + metrics + liveness checks).
3. Clean runbook + acceptance test plan.

---

## 3. Non-Negotiable Requirements

Proposals that violate any of the following are rejected.

1. **Liquidsoap is the playout engine.**

   * No Python/audio streaming in the hot path.
2. **Producer/consumer separation.**

   * If Python dies, Liquidsoap keeps streaming indefinitely.
3. **Pre-buffering is real.**

   * Breaks are fully rendered to disk **≥ 10 minutes** before scheduled play (minimum acceptable **5 minutes**).
4. **Evergreen fallback.**

   * A safety music list exists and is always playable.
5. **Atomic handoffs.**

   * Producers write temp files and publish via atomic rename (`os.replace`).
6. **OS-level scheduling.**

   * `systemd` timers/units preferred (cron acceptable only with strong justification).
7. **Time/DST correctness.**

   * Station timezone pinned (IANA timezone) and behavior across DST transitions is tested.

---

## 4. Reference Architecture

### Always-on (consumer)

* **Icecast** (transmitter)
* **Liquidsoap** (playout engine)

### Best-effort producers (can crash without affecting stream)

* `ingest.py`: one-time/on-demand library ingest + loudness normalization + tagging
* `planner.py`: daily schedule generation
* `news_gen.py`: hourly (at :50) generate next break audio asset
* `enqueue.py`: minutely feed queues + ensure once-per-hour break semantics
* `housekeeping.py`: daily pruning + disk guardrails
* `healthcheck.py`: minutely liveness + alert stub

**Only communication:** filesystem + Liquidsoap unix socket.

---

## 5. File/Folder Layout (Exact Paths)

All implementation must conform to the following layout.

```
/srv/ai_radio/
  assets/
    music/
    beds/
    breaks/
      next.mp3
      last_good.mp3
      archive/YYYY-MM-DD/HH00.mp3
    safety/
      evergreen.m3u
      hourly_bumper.mp3
  drops/
    queue/
    force_break/
    kill_generation/
  state/
    schedule.json
    enqueue_state.json
    metrics.json
  db/
    radio.sqlite3
  logs/
    jobs.jsonl
/run/liquidsoap/
  radio.sock
```

---

## 6. Data Model Requirements

SQLite database: `/srv/ai_radio/db/radio.sqlite3`

### Required tables

**assets**

* `id TEXT PRIMARY KEY` (sha256)
* `path TEXT NOT NULL`
* `kind TEXT NOT NULL` (`music|break|bed|safety`)
* `duration_sec REAL`
* `loudness_lufs REAL`
* `true_peak_dbtp REAL`
* `energy_level INTEGER` (0–100, optional)
* `title TEXT`, `artist TEXT`, `album TEXT`
* `created_at TEXT` (ISO8601 UTC)

**play_history**

* `id INTEGER PRIMARY KEY AUTOINCREMENT`
* `asset_id TEXT NOT NULL`
* `played_at TEXT NOT NULL` (ISO8601 UTC)
* `source TEXT` (`music|override|break|bumper`)
* `hour_bucket TEXT` (e.g., `2025-12-18T15:00:00Z`)

**generation_runs**

* `id INTEGER PRIMARY KEY AUTOINCREMENT`
* `job TEXT` (`planner|news_gen|enqueue|housekeeping|healthcheck`)
* `started_at TEXT`, `finished_at TEXT` (UTC)
* `status TEXT` (`ok|fail|skipped`)
* `error TEXT` (nullable)
* `output_path TEXT` (nullable)

---

## 7. Time, Timezone, and DST Requirements

### Station timezone

* VM must be configured with an explicit IANA timezone (expected: `America/Chicago`).

### Timestamp rules

* **DB and state files store UTC timestamps.**
* **Top-of-hour semantics are station local time.**

### DST acceptance requirement

* Provide a DST-focused acceptance test proving:

  * `news_gen` runs at **local :50**
  * break insertion occurs at **local :00**
  * no double/missed breaks due to DST shift

---

## 8. Audio Engineering Requirements

### Stream encoding

* MP3, **192 kbps CBR**, **44.1 kHz**, stereo

### Loudness targets

* **Integrated:** `-18 LUFS`
* **True peak:** `-1.0 dBTP`

### Where normalization happens

* Music: ingest-time normalization (offline)
* Breaks: render-time mixing + normalization (per break)
* Liquidsoap: crossfade + safety only (no heavy DSP beyond what's needed)

### Required loudness command (or equivalent)

Implementation must include an exact command line equivalent to:

```bash
ffmpeg-normalize INPUT.mp3 \
  --normalization-type ebu \
  --target-level -18 \
  --true-peak -1 \
  --audio-codec libmp3lame \
  --audio-bitrate 192k \
  --output OUTPUT.mp3 \
  --force
```

### News bed mixing

* Must include real ducking/sidechain behavior (bed drops during VO), not just a quiet bed.

---

## 9. Playout Requirements (Liquidsoap)

Contractor must deliver a full `radio.liq` that includes:

1. **Icecast output** (local host + mount)
2. **Crossfade config** (1–2 seconds total)
3. **Multi-level fallback chain**:

   * operator override queue
   * scheduled music queue
   * evergreen playlist
   * safety bumper / technical difficulties
4. **Hourly break insertion** at top-of-hour with once-per-hour guarantee
5. **Break fallback semantics**:

   * Prefer `next.mp3` if present and fresh
   * Else `last_good.mp3`
   * Else `hourly_bumper.mp3`

### Break freshness

* A break is stale if older than **65 minutes** relative to station time.

---

## 10. Human Overrides (Concrete Semantics)

1. **Drop-in "play next"**

   * Any MP3 dropped into `/srv/ai_radio/drops/queue/` plays next (after current crossfade boundary).
   * File is moved/renamed after enqueue to avoid repeated plays.

2. **Force break trigger**

   * `touch /srv/ai_radio/drops/force_break/trigger`
   * Plays a break immediately after current track fade (no mid-track hard cut).
   * Trigger resets automatically.

3. **Kill switch**

   * `touch /srv/ai_radio/drops/kill_generation`
   * AI generation jobs exit early; stream continues indefinitely.

4. **Manual queue visibility**

   * Provide at least: "show queue sizes" and "clear override queue" commands via a small CLI.

---

## 11. Observability Requirements

### Logs

* Structured JSON lines per job in `/srv/ai_radio/logs/jobs.jsonl`:

  * `ts`, `job`, `status`, `duration_ms`, `error`, `output_path`

### Metrics

* Write `/srv/ai_radio/state/metrics.json` minutely:

  * `minutes_of_audio_ready`
  * `bulletin_age_minutes`
  * `generation_fail_rate_24h` (or `ok/fail/skipped` counts)

### Liveness / dead-air detection

* Poll Icecast `/status-json.xsl` and alert on missing mount or unhealthy state.
* Alert mechanism can be a stub (webhook/email) but must be clearly pluggable.

---

## 12. Housekeeping + Disk Safety

* High-water threshold: **90% disk usage**
* Actions on high-water:

  * prune archived breaks (retain last 14 days)
  * prune logs (retain last 7 days)
  * never delete safety assets
* Provide a daily `housekeeping` systemd unit + timer.

---

## 13. systemd Units & Timers (Minimum Set)

Deliver and install these units:

* `ai-radio-icecast.service` (or use native `icecast2` service; Docker only if justified)
* `ai-radio-liquidsoap.service`
* `ai-radio-news.service` + `.timer` (**OnCalendar=*-*-* *:50:00**, `Persistent=true`)
* `ai-radio-planner.service` + `.timer` (daily)
* `ai-radio-enqueue.service` + `.timer` (minutely)
* `ai-radio-drops.path` + `.service` (drop folder watcher)
* `ai-radio-housekeeping.service` + `.timer` (daily)
* `ai-radio-healthcheck.service` + `.timer` (minutely)

All services must:

* run as `ai-radio` user/group
* use least privilege
* write logs to journald
* store secrets in `EnvironmentFile=` or `LoadCredential=` (no secrets in repo)

---

## 14. Acceptance Tests (Contractual)

Contractor must provide a runnable acceptance test plan: `tests/acceptance.md`.

### Required tests

* **T1** Kill Python services → stream continues **30+ minutes**
* **T2** News fetch fails (simulate timeout/500) → bumper/last_good; stream continues
* **T3** TTS down → bumper/last_good; stream continues
* **T4** Missing `next.mp3` → Liquidsoap skips cleanly (no dead air)
* **T5** Disk usage at 90–95% → prune + alert; stream continues
* **T6** Reboot VM → Icecast + Liquidsoap + timers recover automatically
* **DST test**: demonstrate correct :50 generation / :00 insertion across DST change

---

## 15. Runbook + Onboarding Requirements

Deliver `RUNBOOK.md` including:

1. dependency install
2. timezone configuration
3. Icecast verification (`curl` status)
4. Liquidsoap verification (play local MP3)
5. enabling timers
6. verifying next top-of-hour break insertion
7. operator override steps

---

## 16. Scope of Work

### Included

* Full installable system on a fresh Ubuntu VM
* Working Liquidsoap + Icecast streaming
* Music ingest normalization pipeline
* Hourly break generation pipeline using NWS + RSS + LLM + TTS
* Atomic handoff + fallbacks
* systemd orchestration
* Overrides + housekeeping + basic observability
* Acceptance tests + runbook

### Excluded

* Web UI / dashboard
* Live DJ mode
* Monetization/commercial licensing
* Analytics beyond Icecast basics
* Multi-VM or Kubernetes deployment

---

## 17. Deliverables

1. Repository/tarball containing:

   * `radio.liq`
   * Python scripts (minimal dependencies)
   * systemd unit files
   * schema migrations/init scripts
   * `RUNBOOK.md`
   * `tests/acceptance.md`
2. Demonstration on a fresh VM:

   * stream runs continuously for ≥ 2 hours
   * at least one top-of-hour break insertion succeeds
   * live demo of T1–T4 failure recovery

---

## 18. Definition of Done

Work is accepted when:

* all Non-Negotiables are met
* deliverables are complete
* acceptance tests pass
* documentation allows a new operator to bring the station up from scratch

---

## 19. Proposal Response Format (for contractors)

Please respond with:

1. Architecture diagram + narrative
2. Liquidsoap approach (break insertion strategy, fallback chain)
3. Exact toolchain for loudness + mixing (commands)
4. systemd units/timers outline
5. Observability plan (what metrics/logs and where)
6. Acceptance test plan outline (how you'll prove T1–T6 + DST)
7. Risks/assumptions

---

## 20. Assumptions / Inputs We Provide

* RSS feed list
* Station lat/lon for NWS
* API keys for LLM/TTS provider(s)
* Bed audio assets (or contractor can supply simple royalty-free loops if needed)
* Existing music library location for ingest

---

## 21. Change Control

Any scope expansion beyond Section 16 (Scope of Work) requires written approval and an updated estimate.
