# AI Radio Station - Project Status

**Date:** 2025-12-20
**Current Phase:** Phase 4 (Content Generation) - 95% Complete

---

## Phase Completion Summary

### ✅ Phase 0: Foundation & Setup
**Status:** Complete
- Directory structure established
- SQLite database schema created
- Python project initialized with uv
- Configuration management implemented

### ✅ Phase 1: Core Infrastructure (Always-On)
**Status:** Complete
- Icecast2 streaming server running
- Liquidsoap basic configuration operational
- Safety assets (evergreen playlist, bumper)
- systemd services configured
- Stream accessible and broadcasting

### ✅ Phase 2: Database & Asset Management
**Status:** Complete
- Music library ingestion script (`ingest.py`)
- Loudness normalization (-18 LUFS, -1.0 dBTP)
- SHA256 hashing for asset IDs
- Metadata extraction and database population
- Normalized assets in `/srv/ai_radio/assets/music/`

### ✅ Phase 3: Liquidsoap Advanced Configuration
**Status:** Complete
- Multi-level fallback chain (6 levels)
- Break insertion logic
- Operator override queue
- Drop-in file monitoring
- Force break trigger
- Unix socket interface
- Bumpers directory for station IDs

### 🟡 Phase 4: Content Generation Pipeline
**Status:** 95% Complete (In Progress)

**Completed:**
- ✅ Weather data fetching (NWS API) - `weather.py`
- ✅ News aggregation (RSS feeds) - `news.py`
- ✅ LLM script generation (Claude API) - `script_writer.py`
- ✅ TTS voice synthesis (OpenAI + Gemini) - `voice_synth.py`
- ✅ Audio mixing with bed tracks - `audio_mixer.py`
- ✅ Break generation orchestrator - `break_generator.py`
- ✅ Atomic file output to breaks directory
- ✅ Break archival system
- ✅ **Anti-repetition system:**
  - Self-critique two-pass generation
  - Negative examples in prompts
  - Repetition phrase logging (last 60 phrases)
  - Split temperature settings (weather=0.8, news=0.6)

**Remaining:**
- ⏳ Systemd timer for automatic break generation (hourly at :50)
- ⏳ Break freshness checking integration
- ⏳ Sync all Phase 4 code to VM

**Current Work:**
- Recently completed comprehensive weather variety improvements
- Station IDs uploaded to VM (`/srv/ai_radio/assets/bumpers/`)
- Liquidsoap restarted with station IDs loaded

### 🔵 Phase 5: Scheduling & Orchestration
**Status:** Planned (Next Phase)

**Plan Updated:**
- Task 1: Unix socket communication library
- Task 2: Energy-aware track selection
- Task 3: Music enqueue service
- **Task 4: Break scheduler with gap-filling logic (UPDATED 2025-12-20)**
  - Intelligent top-of-hour scheduling
  - Gap calculation between queue end and :00
  - Station ID filler for 30sec-3min gaps
  - Avoids cutting into songs
  - Flexible content insertion
- Task 5: Systemd timers
- Task 6: Integration testing

**Gap-Filling Strategy:**
```
55-59 minutes of hour:
1. Calculate when current queue will end
2. If ends 58-59 min: Perfect, schedule break
3. If gap 30sec-3min: Fill with station ID
4. If gap >3min: Let enqueue service add regular track
5. Schedule break to play at :00
```

### ⬜ Phase 6: Observability & Housekeeping
**Status:** Not Started
- Structured JSON logging
- Metrics generation
- Health checks
- Housekeeping scripts
- Disk management

### ⬜ Phase 7: Operator Tools & CLI
**Status:** Not Started
- CLI command-line tool
- Queue management commands
- Current track info
- Schedule viewing

### ⬜ Phase 8: Testing & Documentation
**Status:** Not Started
- Acceptance tests (T1-T6)
- DST transition testing
- Operator runbook
- Troubleshooting guide

---

## Current System State

**Stream Status:** ✅ Active
- URL: http://radio.clintecker.com:8000/radio
- Format: MP3 192kbps, 44.1kHz stereo
- Current playback: Station IDs (bumpers) in rotation

**Liquidsoap:** ✅ Running
- Service: `ai-radio-liquidsoap.service`
- Config: `/srv/ai_radio/config/radio.liq`
- Socket: `/run/liquidsoap/radio.sock`

**Assets:**
- Music library: Ingested and normalized
- Station IDs: 7 files in `/srv/ai_radio/assets/bumpers/`
- Breaks: Generated on-demand, stored in `/srv/ai_radio/assets/breaks/`
- Beds: Available in `/srv/ai_radio/assets/beds/`

**Configuration:**
- Station: LAST BYTE RADIO, Chicago
- World: Post-capitalist dystopian cyber future
- Announcer: Kore (Gemini TTS voice)
- Temperature: weather=0.8, news=0.6
- Anti-repetition: Active with phrase tracking

---

## Next Steps

1. **Complete Phase 4:**
   - Add systemd timer for hourly break generation
   - Implement break freshness checking
   - Test end-to-end break generation workflow

2. **Begin Phase 5:**
   - Implement gap filler module (`gap_filler.py`)
   - Update break scheduler with gap-filling logic
   - Test top-of-hour scheduling with station IDs

3. **Monitor Stream:**
   - Verify station IDs are playing in rotation
   - Check Liquidsoap fallback chain behavior
   - Confirm no dead air scenarios

---

## Known Issues

- ⚠️ Stream currently playing 440Hz tone or station IDs only (no music queue)
- ⚠️ Music enqueue service not yet implemented (Phase 5)
- ⚠️ Break scheduler not yet automated (Phase 5)
- ⚠️ No automatic content generation timer (Phase 4 remainder)

---

## Recent Changes (2025-12-20)

1. Implemented comprehensive anti-repetition system:
   - Self-critique two-pass weather generation
   - Negative examples in prompts (5 bad/good pairs)
   - Phrase logging (tracks last 60 phrases)
   - Split temperature configuration

2. Fixed critical script generation issues:
   - Added intro/outro structure (LAST BYTE RADIO, Chicago)
   - Lowered temperature to prevent incoherence (1.0 → 0.8)
   - Fixed self-critique output formatting

3. Organized and uploaded station IDs:
   - Renamed 7 files to clean numbered format
   - Uploaded to VM at `/srv/ai_radio/assets/bumpers/`
   - Restarted Liquidsoap to load station IDs

4. Updated Phase 5 plan:
   - Added gap-filling logic for top-of-hour breaks
   - Designed flexible filler content system
   - Integrated station IDs as gap fillers

---

## SOW Compliance

**Current Compliance:** Phases 0-3 fully compliant
**Phase 4:** 95% compliant (missing automation timer)
**Overall Project:** ~70% complete
