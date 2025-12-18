# AI Radio Station Implementation - Phase Overview

> This document outlines the implementation phases for the AI Radio Station MVP. Each phase will have a detailed implementation plan that will be validated by thinking models before execution.

## Phase Strategy

**Core Principle:** Build the always-on streaming infrastructure first, then add intelligent content generation on top. Each phase builds on the previous and can be independently tested.

**Risk Mitigation:** By implementing Icecast + Liquidsoap early, we ensure continuous streaming throughout development. All Python services are best-effort producers that can fail without affecting the stream.

---

## Phase 0: Foundation & Setup
**Duration Estimate:** Foundation work
**Goal:** Establish project structure, directory layout, and database schema

**Deliverables:**
- `/srv/ai_radio/` directory structure per SOW Section 5
- SQLite database schema per SOW Section 6
- `ai-radio` user/group with appropriate permissions
- Python project initialized with `uv` (pyproject.toml)
- Basic configuration management (secrets, paths)

**Success Criteria:**
- All directories exist with correct ownership
- Database can be initialized with schema
- Project can install dependencies via `uv`

**SOW Compliance:**
- ✅ Section 5: File/Folder Layout
- ✅ Section 6: Data Model Requirements
- ✅ Section 13: User/group setup

---

## Phase 1: Core Infrastructure (Always-On)
**Duration Estimate:** Core streaming setup
**Goal:** Get Icecast + Liquidsoap streaming 24/7 with basic fallback

**Deliverables:**
- Icecast2 installed and configured
- Liquidsoap installed with basic `radio.liq`
- Safety assets (evergreen playlist, bumper)
- Basic fallback chain working
- systemd services for Icecast + Liquidsoap

**Success Criteria:**
- Stream accessible at Icecast mount point
- Can play from evergreen playlist continuously
- Services auto-restart on failure
- Services start on boot

**SOW Compliance:**
- ✅ Section 3: Non-Negotiable #1 (Liquidsoap is playout engine)
- ✅ Section 3: Non-Negotiable #4 (Evergreen fallback)
- ✅ Section 8: Stream encoding (192kbps MP3)
- ✅ Section 9: Icecast output + basic fallback
- ✅ Section 13: systemd services

---

## Phase 2: Database & Asset Management
**Duration Estimate:** Asset pipeline setup
**Goal:** Ingest music library with loudness normalization

**Deliverables:**
- `ingest.py` script for music library processing
- Loudness normalization using ffmpeg-normalize
- SHA256 hashing for asset IDs
- Metadata extraction (title, artist, album, duration)
- Database population with normalized assets

**Success Criteria:**
- Can ingest entire music library (~1,000 tracks)
- All tracks normalized to -18 LUFS, -1.0 dBTP
- Asset metadata in database
- Normalized files in `/srv/ai_radio/assets/music/`

**SOW Compliance:**
- ✅ Section 4: `ingest.py` architecture
- ✅ Section 6: Assets table schema
- ✅ Section 8: Loudness targets + ffmpeg-normalize
- ✅ Section 3: Non-Negotiable #5 (Atomic handoffs)

---

## Phase 3: Liquidsoap Advanced Configuration
**Duration Estimate:** Advanced playout logic
**Goal:** Multi-level fallback chain + break insertion + operator overrides

**Deliverables:**
- Complete `radio.liq` with all fallback levels
- Hourly break insertion at top-of-hour
- Break freshness checking (65-minute staleness)
- Operator override queue handling
- Drop-in queue with atomic file handling
- Force break trigger via filesystem
- Crossfade configuration
- Unix socket for telnet interface

**Success Criteria:**
- Fallback chain: override queue → music queue → evergreen → bumper
- Breaks play at top-of-hour with once-per-hour guarantee
- Stale breaks are skipped cleanly
- Can drop MP3 into queue and hear it play next
- Force break trigger works
- No dead air under any fallback scenario

**SOW Compliance:**
- ✅ Section 3: Non-Negotiable #2 (Producer/consumer separation)
- ✅ Section 3: Non-Negotiable #4 (Evergreen fallback)
- ✅ Section 9: All playout requirements
- ✅ Section 10: Human overrides (drop-in, force break)

---

## Phase 4: Content Generation Pipeline
**Duration Estimate:** AI content creation
**Goal:** Generate news/weather breaks with LLM + TTS

**Deliverables:**
- `news_gen.py` script for break generation
- NWS API integration for weather data
- RSS feed aggregation for news
- LLM integration for bulletin scripting
- TTS integration for voice generation
- Bed audio mixing with ducking/sidechain
- Atomic file output to `next.mp3`
- Archival to timestamped files

**Success Criteria:**
- Can fetch weather from NWS API for station lat/lon
- Can aggregate news from RSS feeds
- LLM generates coherent bulletin script
- TTS renders natural voice
- Bed audio ducks during voice
- Output normalized to -18 LUFS, -1.0 dBTP
- Files written atomically via temp + rename

**SOW Compliance:**
- ✅ Section 4: `news_gen.py` architecture
- ✅ Section 3: Non-Negotiable #3 (Pre-buffering ≥5 minutes)
- ✅ Section 3: Non-Negotiable #5 (Atomic handoffs)
- ✅ Section 8: Loudness + bed mixing with ducking
- ✅ Section 5: Break file paths

---

## Phase 5: Scheduling & Orchestration
**Duration Estimate:** Automation setup
**Goal:** Automated scheduling with systemd timers

**Deliverables:**
- `planner.py` for daily schedule generation
- `enqueue.py` for minutely queue feeding
- `schedule.json` and `enqueue_state.json` state management
- systemd units for all services
- systemd timers with correct schedules
- systemd path unit for drops/ monitoring
- Kill switch implementation
- Timezone configuration
- DST-safe scheduling

**Success Criteria:**
- Planner runs daily and generates schedule
- News generation runs at :50 every hour (local time)
- Enqueue runs every minute
- Drops folder monitored for new files
- Kill switch prevents AI generation when active
- DST transitions handled correctly
- All services log to journald

**SOW Compliance:**
- ✅ Section 4: All producer services
- ✅ Section 3: Non-Negotiable #6 (OS-level scheduling)
- ✅ Section 3: Non-Negotiable #7 (Time/DST correctness)
- ✅ Section 7: Timezone requirements
- ✅ Section 10: Kill switch
- ✅ Section 13: All systemd units + timers

---

## Phase 6: Observability & Housekeeping
**Duration Estimate:** Monitoring setup
**Goal:** Logging, metrics, health checks, and disk management

**Deliverables:**
- Structured JSON logging to `jobs.jsonl`
- `metrics.json` generation (minutely)
- `healthcheck.py` with Icecast polling
- Alert stub (webhook/email)
- `housekeeping.py` for pruning old files
- Disk usage monitoring (90% threshold)
- Log rotation strategy

**Success Criteria:**
- All jobs log structured JSON with ts, job, status, duration_ms
- Metrics updated every minute
- Healthcheck detects stream down condition
- Housekeeping prunes breaks >14 days, logs >7 days
- Disk high-water triggers cleanup
- Safety assets never deleted

**SOW Compliance:**
- ✅ Section 4: `housekeeping.py`, `healthcheck.py`
- ✅ Section 11: All observability requirements
- ✅ Section 12: Housekeeping + disk safety

---

## Phase 7: Operator Tools & CLI
**Duration Estimate:** Human interface
**Goal:** Simple CLI for operator control

**Deliverables:**
- `radio_cli.py` command-line tool
- Queue status commands
- Clear queue commands
- Current track info
- Upcoming schedule view
- Force break trigger
- Generation status check

**Success Criteria:**
- `radio_cli queue status` shows queue lengths
- `radio_cli queue clear override` empties override queue
- `radio_cli now-playing` shows current track
- `radio_cli schedule upcoming` shows next 10 tracks
- `radio_cli break force` triggers immediate break
- `radio_cli generation status` shows AI generation state

**SOW Compliance:**
- ✅ Section 10: Manual queue visibility

---

## Phase 8: Testing & Documentation
**Duration Estimate:** Validation work
**Goal:** Acceptance tests + runbook

**Deliverables:**
- `tests/acceptance.md` with executable test plan
- Runbook for operators
- T1-T6 acceptance tests
- DST transition test
- Installation verification checklist
- Troubleshooting guide

**Success Criteria:**
- T1: Kill Python services → stream continues 30+ minutes ✅
- T2: News fetch fails → bumper/last_good; stream continues ✅
- T3: TTS down → bumper/last_good; stream continues ✅
- T4: Missing next.mp3 → skip cleanly ✅
- T5: Disk 90-95% → prune + alert ✅
- T6: Reboot → auto-recovery ✅
- DST: Correct :50/:00 timing across DST shift ✅
- Runbook allows new operator to deploy from scratch

**SOW Compliance:**
- ✅ Section 14: All acceptance tests
- ✅ Section 15: Runbook requirements
- ✅ Section 18: Definition of Done

---

## Dependencies Between Phases

```
Phase 0 (Foundation)
    ↓
Phase 1 (Core Infrastructure) ←─── Must work before anything else
    ↓
Phase 2 (Asset Management) ←────── Feeds music to Phase 1
    ↓
Phase 3 (Liquidsoap Advanced) ←─── Extends Phase 1 with logic
    ↓
Phase 4 (Content Generation) ←──── Generates breaks for Phase 3
    ↓
Phase 5 (Orchestration) ←────────── Automates Phase 2, 4
    ↓
Phase 6 (Observability) ←────────── Monitors all phases
    ↓
Phase 7 (Operator Tools) ←───────── Controls all phases
    ↓
Phase 8 (Testing & Docs) ←───────── Validates everything

```

## Risk Assessment

**High Risk:**
- Liquidsoap break insertion timing (Phase 3)
- DST transition behavior (Phase 5)
- TTS/LLM API reliability (Phase 4)

**Medium Risk:**
- Loudness normalization quality (Phase 2)
- Filesystem race conditions (Phase 3, 4)
- Disk space management (Phase 6)

**Low Risk:**
- Icecast basic streaming (Phase 1)
- Database schema (Phase 0)
- CLI tooling (Phase 7)

---

## Next Steps

1. Create detailed implementation plan for Phase 0
2. Validate Phase 0 plan with thinking models
3. Iterate until plan satisfies SOW
4. Repeat for each subsequent phase
5. Execute phases sequentially with validation between phases
