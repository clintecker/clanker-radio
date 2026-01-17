# Integration Testing for Scheduled Shows

This document describes integration testing needs for the scheduled AI-generated radio shows feature. All unit tests use mocks; real API integration must be tested manually.

## Overview

The scheduled shows system has external dependencies that require integration testing:

1. **Gemini API** - Script generation and TTS synthesis
2. **Liquidsoap** - Queue management and track playback
3. **Database** - SQLite operations
4. **Filesystem** - Audio file creation and cleanup

## Prerequisites

Before running integration tests:

```bash
# Set required environment variables
export RADIO_GEMINI_API_KEY="your-api-key-here"

# Ensure Liquidsoap is running
make status-liquidsoap  # Or check manually

# Ensure database exists
ls -lh /srv/ai_radio/db/radio.sqlite3
```

## Test 1: Topic Research (Gemini API)

**Purpose**: Verify Gemini API responds with valid topics

**Command**:
```bash
uv run python3 -c "
from ai_radio.show_generator import research_topics
topics = research_topics('Bitcoin news', 'Latest developments')
print(f'✓ Researched {len(topics)} topics:')
for i, topic in enumerate(topics, 1):
    print(f'  {i}. {topic}')
"
```

**Expected**:
- Returns 3-5 topic strings
- Each topic is a complete sentence
- Topics are relevant to "Bitcoin news"
- No API errors or timeouts

**Failure modes**:
- `ValueError: RADIO_GEMINI_API_KEY not configured` → Set API key
- `RuntimeError: Failed to research topics` → Check API quota/network
- Malformed JSON → Report to Gemini team

## Test 2: Script Generation (Gemini API)

**Purpose**: Verify Gemini generates valid multi-speaker scripts

**Command**:
```bash
uv run python3 -c "
from ai_radio.show_generator import generate_interview_script
topics = ['AI regulation debate', 'GPT-5 release']
personas = [
    {'name': 'Sarah', 'traits': 'curious host'},
    {'name': 'Dr. Chen', 'traits': 'AI expert'}
]
script = generate_interview_script(topics, personas)
print(f'✓ Generated script: {len(script)} chars')
print(f'✓ Speaker tags: {script.count(\"[speaker:\")} found')
print('First 500 chars:')
print(script[:500])
"
```

**Expected**:
- Returns string ~1,200 words
- Contains `[speaker: Sarah]` and `[speaker: Dr. Chen]` tags
- Natural Q&A dialogue format
- No API errors

**Failure modes**:
- Missing speaker tags → Adjust prompts
- Too short/long → Check word count constraints
- Wrong format → Validate prompt template

## Test 3: Audio Synthesis (Gemini TTS)

**Purpose**: Verify multi-speaker TTS produces valid audio

**Command**:
```bash
uv run python3 -c "
from pathlib import Path
from ai_radio.show_generator import synthesize_show_audio
script = '[speaker: Sarah] Welcome to the show! [speaker: Dr. Chen] Thanks for having me!'
personas = [
    {'name': 'Sarah', 'traits': 'curious host'},
    {'name': 'Dr. Chen', 'traits': 'AI expert'}
]
output = Path('/tmp/test_show_audio.mp3')
audio = synthesize_show_audio(script, personas, output)
print(f'✓ Audio synthesized: {audio.file_path}')
print(f'✓ Duration: {audio.duration_estimate:.1f}s')
print(f'✓ Voices: {audio.voice}')
print(f'✓ File size: {output.stat().st_size} bytes')
"
```

**Expected**:
- Creates MP3 file at /tmp/test_show_audio.mp3
- File size > 10KB
- Duration estimate reasonable (~30s for test script)
- Voice field lists both speakers
- File is playable

**Verify audio**:
```bash
# Check file format
file /tmp/test_show_audio.mp3

# Play audio (macOS)
afplay /tmp/test_show_audio.mp3

# Check audio properties
ffprobe /tmp/test_show_audio.mp3 2>&1 | grep -E "Duration|Audio"
```

**Failure modes**:
- Empty file → Check Gemini TTS API response
- ffmpeg failure → Check ffmpeg installation
- Garbled audio → Verify PCM parameters (24kHz, 16-bit, mono)

## Test 4: End-to-End Show Generation

**Purpose**: Verify complete pipeline from research to ready show

**Setup**:
```bash
# Create test schedule in database
uv run python3 -c "
from ai_radio.show_repository import ShowRepository
from ai_radio.show_models import ShowSchedule, GeneratedShow
from datetime import datetime, date
from ai_radio.config import config

repo = ShowRepository(str(config.paths.db_path))

# Create test schedule
schedule = ShowSchedule(
    name='Integration Test Show',
    format='interview',
    topic_area='Technology trends',
    days_of_week='[1,2,3,4,5]',  # Weekdays
    start_time='14:00',
    duration_minutes=8,
    timezone='US/Eastern',
    personas='[{\"name\": \"Host\", \"traits\": \"curious\"}, {\"name\": \"Expert\", \"traits\": \"knowledgeable\"}]',
    content_guidance='Focus on AI developments',
    regenerate_daily=True,
    active=True
)

schedule_id = repo.create_schedule(schedule)
print(f'✓ Created schedule ID: {schedule_id}')

# Create pending show for today
show_id = ... # Insert into generated_shows table
print(f'✓ Created show ID: {show_id}')
"
```

**Run generation**:
```bash
uv run python3 -c "
from ai_radio.show_generator import ShowGenerator
from ai_radio.show_repository import ShowRepository
from ai_radio.config import config

repo = ShowRepository(str(config.paths.db_path))
generator = ShowGenerator(repo)

# Get schedule and show from database
schedule = repo.get_schedule(schedule_id)
show = ... # Query generated_shows

# Generate complete show
generator.generate(schedule, show)

# Verify final state
updated_show = ... # Query again
assert updated_show.status == 'ready', f'Expected ready, got {updated_show.status}'
assert updated_show.asset_id is not None, 'Asset ID should be set'
print(f'✓ Show generation complete: {updated_show.asset_id}')
"
```

**Verify results**:
```bash
# Check database state
sqlite3 /srv/ai_radio/db/radio.sqlite3 "
SELECT status, asset_id, length(script_text) as script_len
FROM generated_shows
WHERE id = <show_id>;
"

# Check asset file exists
find /srv/ai_radio/music -name "<asset_id>.mp3"

# Play generated show
afplay /srv/ai_radio/music/<asset_id>.mp3
```

**Expected**:
- Show status transitions: pending → script_complete → ready
- Script text saved (~1,200 words)
- Asset ID populated
- Audio file exists and is playable
- No error_message in database

## Test 5: Liquidsoap Integration

**Purpose**: Verify polling script enqueues shows correctly

**Setup**:
```bash
# Ensure a ready show exists for current time
# Adjust schedule start_time to current hour:minute
```

**Run polling**:
```bash
uv run python3 scripts/schedule_shows.py
```

**Check logs**:
```bash
# Look for enqueue success
grep "Enqueued show" /tmp/schedule_shows.log

# Check Liquidsoap queue
make check-queue
```

**Verify in Liquidsoap**:
```bash
# Connect to Liquidsoap telnet
telnet localhost 1234
> breaks.queue
# Should show enqueued show asset
```

**Expected**:
- Polling script runs without errors
- Matching schedule detected
- Ready show found for current date
- Asset enqueued to 'breaks' queue
- Show airs at scheduled time

**Failure modes**:
- "Show not ready" warning → Check show generation completed
- Enqueue failure → Check Liquidsoap connection
- Wrong time → Verify timezone conversion

## Test 6: DST Transitions

**Purpose**: Verify scheduling works during DST transitions

**Spring Forward Test** (March 2026):
```bash
# Set system time to March 9, 2026 at 2:30 AM ET
# (This time doesn't exist due to DST spring forward)

# Schedule a show for 2:30 AM
# Run polling script
# Expected: Show doesn't air (time skipped)
```

**Fall Back Test** (November 2026):
```bash
# Set system time to November 1, 2026 at 2:00 AM ET (first occurrence)
# Schedule a show for 2:00 AM
# Run polling script
# Expected: Show airs during first occurrence only
```

## Test 7: Error Recovery

**Purpose**: Verify system handles failures gracefully

**Script generation failure**:
```bash
# Set invalid API key temporarily
export RADIO_GEMINI_API_KEY="invalid"

# Run generation
# Expected: status = 'script_failed', error_message populated
```

**Audio synthesis failure**:
```bash
# Create show with script but break ffmpeg
mv /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg.bak

# Run generation from script_complete
# Expected: status = 'audio_failed', error_message populated

# Restore ffmpeg
mv /usr/local/bin/ffmpeg.bak /usr/local/bin/ffmpeg
```

**Orphaned asset cleanup**:
```bash
# Simulate DB failure after ingestion
# Expected: Asset file and DB record both cleaned up
```

## Test 8: Temp File Cleanup

**Purpose**: Verify temp files are always cleaned up

**Test**:
```bash
# Count temp files before
BEFORE=$(ls /tmp/show_*.mp3 2>/dev/null | wc -l)

# Run generation (success case)
# ... generate show ...

# Count temp files after
AFTER=$(ls /tmp/show_*.mp3 2>/dev/null | wc -l)

# Expected: BEFORE == AFTER (no temp file leak)
```

**Test with failure**:
```bash
# Trigger synthesis failure
# Expected: Temp file still cleaned up (finally block)
```

## Automated Integration Testing (Future)

To automate these tests in CI/CD:

1. **Mock Gemini API**: Create local mock server that returns valid responses
2. **Test Liquidsoap**: Use docker-compose for isolated Liquidsoap instance
3. **Test Database**: Use in-memory SQLite for speed
4. **Fixture Audio**: Pre-generate test audio files

Example pytest integration test structure:
```python
@pytest.mark.integration
def test_end_to_end_show_generation(real_db, real_liquidsoap):
    """Integration test with real APIs (requires API key)."""
    # ... actual API calls ...
```

Run with: `uv run pytest -m integration --api-key=$GEMINI_KEY`

## Troubleshooting

**API quota exceeded**:
- Check Gemini API dashboard
- Wait for quota reset or upgrade plan

**Liquidsoap connection refused**:
- Check service status: `systemctl status ai-radio-liquidsoap`
- Verify telnet port: `netstat -an | grep 1234`

**Database locked**:
- Check for concurrent writes
- Increase SQLite timeout in connection

**Audio format issues**:
- Verify ffmpeg version: `ffmpeg -version`
- Check supported codecs: `ffmpeg -codecs | grep mp3`

## Success Criteria

All integration tests pass when:
- ✅ Gemini API returns valid responses
- ✅ TTS produces playable multi-speaker audio
- ✅ End-to-end generation completes (pending → ready)
- ✅ Shows enqueue to Liquidsoap at scheduled times
- ✅ DST transitions handled correctly
- ✅ Errors captured and reported properly
- ✅ No resource leaks (temp files, orphaned assets)

## Next Steps

1. Run all integration tests manually
2. Document any failures or edge cases
3. Create automated integration test suite
4. Add monitoring/alerting for production failures
