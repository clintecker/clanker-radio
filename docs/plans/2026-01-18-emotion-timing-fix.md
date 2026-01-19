# Fix TTS Emotion & Interference Synchronization

**Date**: 2026-01-18
**Status**: Planning

## Problem Statement

Current JSON schema workflow produces poor audio quality:

1. **Halting, robotic TTS** - no emotion variation in questions/answers
2. **Desynchronized interference** - static plays but speaker doesn't acknowledge it
3. **No background music** - path configuration issue
4. **LLM hallucination** - identifies 4 interference points when only 2 acknowledgments exist

## Root Causes

### 1. Emotion Stripping
Renderer (`script_renderer.py`) hardcodes only 5 emotion tags:
- Cold open (3 lines): whispering, shocked, embarrassed
- Signoff (1 line): determined
- **All Q&A (10-15 lines): ZERO emotions**

Result: TTS sounds robotic/halting

### 2. LLM Hallucination
Current flow:
```
Render (with 2 acknowledgments) → Synthesize → STT → LLM analyzes transcript
→ LLM finds 4 "interference points" (hallucinates 2 extra)
→ Static plays at wrong times
```

LLM interprets random phrases as acknowledgments when they're not.

### 3. No Background Beds
Production path `/srv/ai_radio/assets/beds` not found locally.

## Solution Architecture

### Approach: Deterministic Tracking + Emotion Injection

**Key Insight**: Don't ask LLM to "interpret" acknowledgments. We KNOW exactly which phrases we inserted and where.

```
Generate JSON → Validate → Repair → Compress
  → Enhanced Render (emotions + track phrases)
  → Synthesize
  → STT + Direct String Matching (find EXACT phrases)
  → Place interference (BEFORE exact timestamps)
  → Add background beds
```

---

## Implementation Tasks

### Task 1: Enhanced Renderer with Emotion Injection

**File**: `src/ai_radio/script_renderer.py`

**Changes**:

1. Add emotion analysis functions:
```python
def analyze_question_emotion(question: str) -> str:
    """Choose emotion based on question content/keywords."""
    keywords = {
        "why": "curious",
        "how": "interested",
        "challenges": "concerned",
        "what": "curious",
        "can you": "interested"
    }
    # Return appropriate emotion or random from pool

def analyze_answer_emotion(answer: str) -> str:
    """Choose emotion based on answer content/sentiment."""
    keywords = {
        "fight": "determined",
        "hope": "hopeful",
        "struggle": "worried",
        "together": "passionate",
        "community": "earnest"
    }
    # Return appropriate emotion or random from pool
```

2. Modify `render_script()` signature:
```python
def render_script(
    script: FieldReportScript,
    presenter: str,
    source: str
) -> tuple[str, dict]:
    """
    Returns:
        (rendered_script, metadata) where metadata contains:
        {
            "acknowledgment_phrases": [
                {"line_num": 5, "phrase": "Nice try, corps", "timestamp": None},
                {"line_num": 12, "phrase": "Damn corp jammers", "timestamp": None}
            ],
            "total_lines": 25,
            "total_words": 455
        }
    """
```

3. Add emotions to all dialogue:
```python
# Questions
emotion = analyze_question_emotion(segment.question)
lines.append(f"[speaker: {presenter}] [{emotion}] {segment.question}")

# Answers
emotion = analyze_answer_emotion(segment.answer)
lines.append(f"[speaker: {source}] [{emotion}] {segment.answer}")

# Track acknowledgment phrases
if segment.interference_after:
    phrase_template = random.choice(INTERFERENCE_TEMPLATES)
    # Extract actual phrase (strip emotion tags)
    phrase_text = re.sub(r'\[.*?\]', '', phrase_template).strip()

    metadata["acknowledgment_phrases"].append({
        "line_num": len(lines),
        "phrase": phrase_text,  # "Damn corp jammers... where was I?"
        "timestamp": None  # Filled in after STT
    })

    lines.append(f"[speaker: {presenter}] {phrase_template}")
```

4. Add random pauses between exchanges:
```python
if random.random() < 0.3:
    lines[-1] += random.choice([" [short pause]", " [medium pause]"])
```

**Test**: Unit test that emotions are added to all Q&A lines

---

### Task 2: Deterministic Interference Timing

**File**: `src/ai_radio/show_generator.py`

**Changes**:

1. Add exact phrase matching function:
```python
def find_exact_phrase_timestamps(
    word_timestamps: list[dict],
    acknowledgment_phrases: list[dict]
) -> list[dict]:
    """
    Find exact timestamps of acknowledgment phrases in transcript.

    Args:
        word_timestamps: From Whisper STT
        acknowledgment_phrases: From renderer metadata

    Returns:
        Updated acknowledgment_phrases with timestamps filled in
    """
    # Build transcript string
    transcript = " ".join([w["word"] for w in word_timestamps])

    for ack in acknowledgment_phrases:
        # Find phrase in transcript (fuzzy matching for STT errors)
        # Use difflib or simple substring search
        # When found, get timestamp of first word
        # Fill in ack["timestamp"]

    return acknowledgment_phrases
```

2. Update `add_pirate_radio_effects()`:
```python
def add_pirate_radio_effects(
    input_audio: Path,
    output_audio: Path,
    script_text: str = None,
    interference_metadata: dict = None,  # NEW from renderer
    use_stt_timing: bool = True,
    ...
) -> None:
```

3. New timing logic:
```python
if interference_metadata:
    # Preferred: Exact phrase matching
    acknowledgment_phrases = interference_metadata["acknowledgment_phrases"]

    # STT to get word timestamps
    word_timestamps = extract_word_timestamps_with_whisper(input_audio)

    # Find exact phrases
    phrases_with_times = find_exact_phrase_timestamps(
        word_timestamps,
        acknowledgment_phrases
    )

    # Place interference 0.5-1s BEFORE each phrase
    interference_times = [
        max(0, p["timestamp"] - random.uniform(0.5, 1.0))
        for p in phrases_with_times
        if p["timestamp"] is not None
    ]

    logger.info(
        f"Exact phrase matching: {len(interference_times)} "
        f"interference points from {len(acknowledgment_phrases)} phrases"
    )

elif script_text and use_stt_timing:
    # Fallback: LLM interpretation (keep existing code)
    ...
```

**Test**: Verify interference count matches acknowledgment count

---

### Task 3: Background Beds Configuration

**File**: `src/ai_radio/config/base.py`

**Changes**:

1. Add configurable beds paths:
```python
class PathsConfig(BaseModel):
    beds_dir: Path = Field(
        default=Path("/srv/ai_radio/assets/beds"),
        description="Background music beds directory (production)"
    )

    @property
    def beds_dir_resolved(self) -> Path | None:
        """Return beds directory if it exists, None otherwise."""
        # Check environment variable first
        if env_path := os.getenv("AI_RADIO_BEDS_DIR"):
            path = Path(env_path)
            if path.exists():
                return path

        # Check configured path
        if self.beds_dir.exists():
            return self.beds_dir

        # Check common local paths
        for local_path in [
            Path.home() / "Music" / "radio-beds",
            Path.cwd() / "assets" / "beds",
            Path("/tmp") / "radio-beds"
        ]:
            if local_path.exists():
                return local_path

        return None
```

2. Update `show_generator.py`:
```python
beds_dir = config.paths.beds_dir_resolved
if beds_dir is None:
    logger.warning(
        "No background beds directory found. Checked:\n"
        f"  - {config.paths.beds_dir}\n"
        f"  - $AI_RADIO_BEDS_DIR\n"
        f"  - ~/Music/radio-beds\n"
        f"  - ./assets/beds\n"
        "Background music will be skipped."
    )
    # Skip beds, continue without error
else:
    logger.info(f"Using beds directory: {beds_dir}")
    # Proceed with bed selection
```

3. Add to `.env.example`:
```bash
# Optional: Local background music directory
# AI_RADIO_BEDS_DIR=/Users/you/Music/radio-beds
```

**Documentation**: Add section to README about obtaining royalty-free radio beds

---

### Task 4: Integration & Testing

**Files**: `scripts/test_cold_open.py`, integration tests

**Changes**:

1. Update `test_cold_open.py`:
```python
# Render with emotion injection
rendered_script, metadata = render_script(script, presenter_name, source_name)

print(f"📊 Metadata:")
print(f"   Acknowledgment phrases: {len(metadata['acknowledgment_phrases'])}")
for ack in metadata['acknowledgment_phrases']:
    print(f"   - Line {ack['line_num']}: {ack['phrase'][:50]}...")

# Synthesize with metadata for timing
audio_file = synthesize_show_audio(
    script_text=rendered_script,
    personas=personas,
    output_path=output_path,
    add_bed=True,
    interference_metadata=metadata  # NEW
)
```

2. Manual testing checklist:
```
□ Generate new audio
□ Listen for natural emotion variation
□ Count interference bursts (should match acknowledgment count)
□ Verify static plays BEFORE "Damn corp jammers" is said
□ Verify background music plays (if beds available)
□ Compare to old working system
```

3. Update tests:
```python
def test_renderer_returns_metadata():
    """Renderer returns metadata with acknowledgment tracking."""
    script, metadata = render_script(...)
    assert "acknowledgment_phrases" in metadata
    assert len(metadata["acknowledgment_phrases"]) == 2  # Match interference_after flags

def test_interference_count_matches_acknowledgments():
    """Interference timing uses exact phrase matching."""
    # Generate audio with known acknowledgments
    # Verify interference count == acknowledgment count
```

---

## Success Criteria

1. ✅ TTS sounds natural with varied emotions (not robotic/halting)
2. ✅ Interference count matches acknowledgment count (no hallucination)
3. ✅ Interference static plays BEFORE acknowledgment phrases (synchronized)
4. ✅ Background music plays if beds available
5. ✅ All existing tests pass
6. ✅ Audio quality comparable to old working system

---

## Risk Mitigation

**Risk 1: Emotion injection makes scripts too verbose**
- Mitigation: Use emotions sparingly (50% of lines)
- Test with varied content

**Risk 2: STT errors prevent phrase matching**
- Mitigation: Use fuzzy matching (difflib, edit distance)
- Log unmatched phrases for debugging
- Fall back to LLM if < 50% phrases matched

**Risk 3: Breaking existing functionality**
- Mitigation: Renderer returns tuple, but handle callers expecting string
- Run full test suite after each task

**Risk 4: Background beds licensing**
- Mitigation: Document royalty-free sources
- System works without beds (graceful degradation)

---

## Testing Strategy

### Unit Tests
- Renderer adds emotions to all Q&A
- Renderer tracks acknowledgment phrases in metadata
- Phrase matching finds exact timestamps

### Integration Tests
- End-to-end with metadata passthrough
- Interference count == acknowledgment count
- No hallucinated interference points

### Manual Verification
- Listen to generated audio
- Count interference bursts manually
- Verify synchronization

---

## Open Questions

1. **Emotion variety**: How many different emotions should we use? Too many might sound chaotic.
2. **Fuzzy matching threshold**: How lenient should phrase matching be for STT errors?
3. **Beds sources**: Where should we direct users to get royalty-free radio beds?

---

## References

**Current Code**:
- Renderer: `src/ai_radio/script_renderer.py`
- Audio synthesis: `src/ai_radio/show_generator.py` (line 505+)
- Config: `src/ai_radio/config/base.py`

**Related Docs**:
- JSON Schema Workflow: `docs/json-schema-workflow.md`
- Systematic Debugging notes: `docs/plans/2026-01-18-systematic-debugging-notes.md` (user reported issues)
