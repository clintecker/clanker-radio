# Scheduled AI-Generated Radio Shows - Design Document

**Date:** 2026-01-17
**Status:** Design
**Authors:** CLiNT, Claude, PAL (Gemini 2.5 Pro)

## Overview

Add scheduled AI-generated radio show capability to Clanker Radio. Users provide natural language schedule descriptions ("Monday-Friday 9-10am, two crypto analysts discuss Bitcoin news"), which the system converts to structured schedules. Shows are automatically generated overnight and aired at configured times.

## Requirements

### User Experience
- **Input:** Natural language schedule description
- **Review:** System parses to structured format for user confirmation/editing
- **Automation:** Shows generated overnight, aired automatically
- **Fallback:** If generation fails, music continues (no dead air)

### Technical Constraints
- **Show Duration:** 8 minutes (~1,200 words dialogue)
- **API Limits:** Gemini TTS 8,000 byte limit (prompt + script)
- **Generation Window:** Overnight batch (midnight-2am, exact timing TBD)
- **Formats:** Interview (host + expert) and Two-Host Discussion

### Success Criteria
- User can create schedules via natural language
- Shows generate reliably (>90% success rate)
- Audio quality matches existing news breaks
- System handles failures gracefully (music fallback)
- No dead air from failed generation

## Architecture

### System Components

```
┌─────────────────┐
│  User Input     │
│  "M-F 9am..."   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Schedule Parser │  ← Gemini parses NL → JSON
│ (User confirms) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ show_schedules  │  ← SQLite table
│    (DB)         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Overnight Generator Service    │
│  (midnight-2am, systemd timer)  │
│                                 │
│  For each schedule:             │
│  1. Check if show needed today  │
│  2. Research topics (web search)│
│  3. Generate script (Gemini)    │
│  4. Generate audio (Gemini TTS) │
│  5. Ingest to assets            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│ generated_shows │  ← State tracking
│ + assets table  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Liquidsoap     │  ← Polls DB every minute
│  Scheduler      │     Enqueues if status='ready'
└─────────────────┘
```

### Data Flow

1. **Schedule Creation:** User → Parser → Confirmation UI → DB
2. **Overnight Generation:** Timer → Query schedules → Generate (Research → Script → TTS) → Assets
3. **Broadcast:** Liquidsoap polls DB → Finds ready show → Enqueues asset → Airs

## Database Schema

### Table: `show_schedules`

```sql
CREATE TABLE show_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "Crypto Morning Show"
    format TEXT NOT NULL CHECK(format IN ('interview', 'two_host_discussion')),
    topic_area TEXT NOT NULL,              -- "Bitcoin and DeFi news"

    -- Timing
    days_of_week TEXT NOT NULL,            -- JSON: [1,2,3,4,5] for M-F
    start_time TEXT NOT NULL,              -- "09:00" (24-hour)
    duration_minutes INTEGER DEFAULT 8,
    timezone TEXT DEFAULT 'America/New_York',

    -- Show configuration
    personas TEXT NOT NULL,                 -- JSON: [{"name": "Marco", "traits": "skeptical, data-driven"}, ...]
    content_guidance TEXT,                  -- User's bullet points/topics
    regenerate_daily BOOLEAN DEFAULT 1,     -- 1=regenerate, 0=evergreen

    -- State
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schedules_active ON show_schedules(active);
```

**Design Notes:**
- JSON storage for `days_of_week` and `personas` (flexible, no extra JOINs)
- CHECK constraint enforces valid formats
- `regenerate_daily` allows evergreen content caching
- Timezone explicit (prevents ambiguity)

### Table: `generated_shows`

```sql
CREATE TABLE generated_shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,
    air_date DATE NOT NULL,                -- "2026-01-18"

    -- State machine
    status TEXT NOT NULL CHECK(status IN (
        'pending',
        'script_complete',
        'ready',
        'script_failed',
        'audio_failed'
    )),
    retry_count INTEGER DEFAULT 0,         -- Max 3 retries

    -- Artifacts
    script_text TEXT,                      -- Saved even if TTS fails
    asset_id INTEGER,                      -- FK to assets (once audio ready)

    -- Metadata
    generated_at TIMESTAMP,
    error_message TEXT,

    UNIQUE(schedule_id, air_date),         -- Idempotency
    FOREIGN KEY(schedule_id) REFERENCES show_schedules(id) ON DELETE CASCADE,
    FOREIGN KEY(asset_id) REFERENCES assets(id)
);

CREATE INDEX idx_generated_shows_status_air_date ON generated_shows(status, air_date);
```

**Design Notes:**
- **State Machine:** Separates script vs audio failures for targeted retries
- **retry_count:** Prevents infinite retry loops (max 3)
- **script_text preservation:** Allows TTS retry without re-scripting
- **UNIQUE constraint:** Prevents race conditions (atomic insert)
- **CASCADE delete:** Auto-cleanup when schedule deleted

### State Machine Flow

```
pending
  ├──→ script_complete ──→ ready (success!)
  ├──→ script_failed (retry if count < 3)
  └──→ audio_failed (retry TTS only, reuse script)
```

## Generation Pipeline

### Overnight Generator Workflow

```python
# Runs midnight-2am (exact time TBD after benchmarking)
def generate_scheduled_shows():
    # 1. Query active schedules
    schedules = db.query("SELECT * FROM show_schedules WHERE active = 1")

    for schedule in schedules:
        # 2. Check if show needed today
        if today.weekday() not in schedule.days_of_week:
            continue

        # 3. Idempotency check
        show = db.query(
            "SELECT * FROM generated_shows WHERE schedule_id = ? AND air_date = ?",
            schedule.id, today
        )

        if show and show.status == 'ready':
            continue  # Already done

        if show and show.status in ['script_failed', 'audio_failed']:
            if show.retry_count >= 3:
                continue  # Give up, poison pill

        if not show:
            # Create new record
            show = db.insert("generated_shows", {
                'schedule_id': schedule.id,
                'air_date': today,
                'status': 'pending'
            })

        # 4. Generate (with timeouts and retries)
        try:
            generate_show(schedule, show)
        except Exception as e:
            log.error(f"Show {show.id} failed: {e}")
            # Continue to next show (don't block entire batch)
```

### Show Generation Steps

```python
def generate_show(schedule, show):
    # Step 1: Script Generation (state-aware)
    if show.status in ['pending', 'script_failed']:
        try:
            # Research topics
            topics = research_topics(schedule.topic_area, schedule.content_guidance)

            # Generate dialogue using format-specific template
            if schedule.format == 'interview':
                script = generate_interview_script(topics, schedule.personas)
            else:
                script = generate_discussion_script(topics, schedule.personas)

            # Validate output
            validate_script(script, max_words=1200, max_bytes=7500)

            # Save and update status
            db.update(show.id, {
                'script_text': script,
                'status': 'script_complete',
                'generated_at': now()
            })

        except Exception as e:
            db.update(show.id, {
                'status': 'script_failed',
                'error_message': str(e),
                'retry_count': show.retry_count + 1
            })
            raise

    # Step 2: Audio Generation (reuses existing script)
    if show.status in ['script_complete', 'audio_failed']:
        try:
            # Generate audio with Gemini TTS
            audio_file = synthesize_audio(
                script_text=show.script_text,
                personas=schedule.personas,
                voice='Kore'
            )

            # Validate audio
            validate_audio(audio_file, expected_duration_minutes=8)

            # Ingest to assets
            asset = ingest_audio_file(
                source_path=audio_file,
                kind='scheduled_show',
                metadata={
                    'schedule_id': schedule.id,
                    'show_name': schedule.name
                }
            )

            # Mark ready
            db.update(show.id, {
                'asset_id': asset.id,
                'status': 'ready'
            })

        except Exception as e:
            db.update(show.id, {
                'status': 'audio_failed',
                'error_message': str(e),
                'retry_count': show.retry_count + 1
            })
            raise
```

### Prompt Templates

**Interview Format:**
```python
def generate_interview_script(topics, personas):
    host = personas[0]
    expert = personas[1]

    prompt = f"""Generate an 8-minute interview-style radio dialogue (~1,200 words).

# PERSONAS
- Host: {host['name']} - {host['traits']}
- Expert: {expert['name']} - {expert['traits']}

# TOPICS TO COVER
{format_topics(topics)}

# OUTPUT FORMAT
Use speaker aliases exactly as shown:
[speaker: {host['name']}] Dialogue here...
[speaker: {expert['name']}] Response here...

# CONSTRAINTS
- Exactly 1,200 words (±50 words)
- Output MUST be under 7,500 bytes
- Natural Q&A flow: question → answer → follow-up
- End with host thanking expert

Generate the dialogue now:"""

    return call_gemini(prompt)
```

**Two-Host Discussion:**
```python
def generate_discussion_script(topics, personas):
    host_a = personas[0]
    host_b = personas[1]

    prompt = f"""Generate an 8-minute two-host discussion (~1,200 words).

# PERSONAS
- {host_a['name']}: {host_a['traits']}
- {host_b['name']}: {host_b['traits']}

# TOPICS TO COVER
{format_topics(topics)}

# STRUCTURE
1. {host_a['name']} opens with topic 1 overview
2. {host_b['name']} presents contrasting perspective
3. Debate/discuss with back-and-forth
4. Move to topics 2-3 with similar dynamic
5. {host_b['name']} closes with synthesis

# OUTPUT FORMAT
[speaker: {host_a['name']}] Dialogue here...
[speaker: {host_b['name']}] Response here...

# CONSTRAINTS
- Exactly 1,200 words (±50 words)
- Output MUST be under 7,500 bytes
- Create genuine disagreement/contrast (not just agreement)
- Avoid "I agree" or "great point" filler

Generate the dialogue now:"""

    return call_gemini(prompt)
```

## Implementation Components

### 1. Schedule Parser (`src/ai_radio/schedule_parser.py`)

```python
class ScheduleParser:
    """Parses natural language schedule descriptions into structured format."""

    def parse(self, user_input: str) -> ScheduleProposal:
        """Parse natural language to structured schedule.

        Returns proposal for user confirmation (not auto-saved).
        """
        prompt = f"""Parse this radio show schedule description into structured JSON:

"{user_input}"

Return JSON with these fields:
{{
    "name": "User-friendly show name",
    "format": "interview" or "two_host_discussion",
    "topic_area": "What the show discusses",
    "days_of_week": [1,2,3,4,5],  // 0=Sunday, 6=Saturday
    "start_time": "09:00",  // 24-hour format
    "duration_minutes": 8,
    "personas": [
        {{"name": "Marco", "traits": "skeptical, data-driven analyst"}},
        {{"name": "Chloe", "traits": "optimistic, long-term strategist"}}
    ],
    "content_guidance": "Topics/bullet points extracted from description"
}}"""

        response = call_gemini(prompt)
        return ScheduleProposal.from_json(response)
```

### 2. Show Generator (`src/ai_radio/show_generator.py`)

Similar structure to existing `break_generator.py`:
- Orchestrates research → script → TTS pipeline
- State-aware (resumes from last successful step)
- Updates `generated_shows` table at each stage
- Implements timeouts and retries

### 3. Overnight Service (`scripts/generate_scheduled_shows.py`)

- Runs via systemd timer (midnight-2am)
- Queries schedules, generates missing shows
- Structured logging (JSON key-value pairs)
- Master timeout: 2 hours max

### 4. Liquidsoap Integration

**Polling Script** (runs every minute):
```python
def check_scheduled_shows():
    now = datetime.now()

    # Find schedules that should be airing now
    for schedule in get_active_schedules():
        if should_air_now(schedule, now):
            # Query for ready show
            show = db.query("""
                SELECT asset_id FROM generated_shows
                WHERE schedule_id = ? AND air_date = ? AND status = 'ready'
            """, schedule.id, now.date())

            if show and show.asset_id:
                # Enqueue to breaks queue
                liquidsoap_client.push_track('breaks', get_asset_path(show.asset_id))
                log.info(f"Enqueued show: {schedule.name}")
            else:
                # Not ready - music continues (no action needed)
                log.warning(f"Show not ready: {schedule.name}")
```

## Failure Handling

### Failure Strategy
1. **Generation Failure:** Max 3 retries, then give up
2. **Show Not Ready:** Music continues (existing behavior)
3. **Poison Pill Shows:** Daily summary report of shows at max_retries

### Timeouts
- **API calls:** 30 seconds each (Gemini script, TTS, web search)
- **ffmpeg conversion:** 60 seconds
- **Per-show total:** 10 minutes max
- **Service master:** 2 hours (systemd `TimeoutStopSec`)

### Monitoring & Alerting

**Critical Alerts:**
- Service fails to complete overnight run
- >10% of scheduled shows failed
- Any show at max_retries (daily summary)

**Dashboard Metrics:**
- `shows_generated_total` (by status)
- `show_generation_duration_seconds` (P95)
- `show_generation_retries` (counter)

**Structured Logging:**
```json
{
    "schedule_id": 123,
    "air_date": "2026-01-18",
    "attempt": 2,
    "stage": "script_generation",
    "status": "success",
    "duration_seconds": 45
}
```

## Schedule Conflict Detection

Implemented at application level (not database):

```python
def validate_no_conflicts(new_schedule):
    existing = db.query("SELECT * FROM show_schedules WHERE active = 1")

    for schedule in existing:
        # Check day overlap
        overlapping_days = set(new_schedule.days_of_week) & set(schedule.days_of_week)

        if overlapping_days:
            # Check time overlap
            if times_overlap(
                new_schedule.start_time,
                new_schedule.duration_minutes,
                schedule.start_time,
                schedule.duration_minutes
            ):
                raise ConflictError(f"Conflicts with: {schedule.name}")
```

## Operational Considerations

### Start Time Calculation

**Needs benchmarking:**
1. Measure P95 generation time per show (~5 min expected)
2. Calculate: `P95_time × max_daily_shows × 3x_buffer`
3. Work backward from first airtime
4. Add 1-hour buffer for manual review

**Example:** 20 shows/day × 5 min × 3x = 5 hours → Start at 1am if first show at 7am

### Content Caching

**Evergreen Shows:**
- Set `regenerate_daily = 0`
- Generator checks if asset exists for schedule
- Reuses existing asset if found
- Useful for historical content, recurring segments

**News Shows:**
- Set `regenerate_daily = 1` (default)
- Always generates fresh content
- Uses current topics/news

## Future Enhancements

**Phase 2 Improvements:**
- Single-host monologue format
- News roundup format (multi-segment)
- Web UI for schedule management
- Show preview/approval workflow
- Manual trigger for immediate generation

**Not Recommended:**
- Panel discussion (3+ voices) - too complex, poor quality
- Long Audio Synthesis API - unclear multi-speaker support in preview

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Schedule parser misinterprets input | User confirmation loop before saving |
| Generation hangs/blocks entire batch | Aggressive timeouts, fail fast |
| Race condition on concurrent runs | UNIQUE DB constraint, idempotency checks |
| Poison pill shows (always fail) | Max retries, daily alert report |
| Invalid LLM output | Validation (word count, byte limit, format) |
| TTS audio quality issues | Validate duration, sample rate |
| Dead air if show not ready | Music continues (existing fallback) |

## Implementation Checklist

- [ ] Database migration (add tables, indices)
- [ ] Schedule parser with Gemini integration
- [ ] User confirmation UI for parsed schedules
- [ ] Prompt templates (interview, discussion)
- [ ] Show generator with state machine
- [ ] Topic research integration
- [ ] Audio validation
- [ ] Overnight service with timeouts
- [ ] Liquidsoap polling script
- [ ] Conflict detection logic
- [ ] Monitoring dashboard
- [ ] Alert configuration
- [ ] Benchmark generation time
- [ ] Set optimal start time
- [ ] Integration tests
- [ ] Documentation

## References

- **Gemini TTS Docs:** https://docs.cloud.google.com/text-to-speech/docs/gemini-tts
- **Current System:** `src/ai_radio/break_generator.py` (1-min news breaks)
- **PAL Research:** See conversation thread 7ec5807c-c766-4f48-95d7-6b1336c060ec
