# JSON Schema Script Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace single-pass prompt engineering with JSON schema generation + programmatic rendering to reliably enforce timing and structure constraints.

**Architecture:** Generate structured JSON with explicit segments using Gemini 2.0 Flash, validate structure programmatically, repair violations surgically, and render final script with template-based interference injection. This moves constraint enforcement from prompt (soft) to application logic (hard).

**Tech Stack:** Python 3.11+, Pydantic for data models, Gemini 2.0 Flash with JSON schema, pytest for testing

---

## Background

**Problem:** Current single-pass prompt engineering cannot reliably enforce global constraints (word count, timing, segment placement) because LLMs generate token-by-token and cannot retroactively satisfy constraints.

**Solution:** JSON schema with per-segment budgets + programmatic rendering with interference templates.

**Expert Consensus:** Both GPT-5.2 and Gemini-3-Pro (9/10 confidence) agree this requires architectural changes, not better prompting.

---

## Task 1: Define Pydantic Models for Structured Script

**Files:**
- Create: `src/ai_radio/models/script_schema.py`
- Test: `tests/ai_radio/models/test_script_schema.py`

**Step 1: Write the failing test**

```python
# tests/ai_radio/models/test_script_schema.py
"""Tests for script schema data models."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript


def test_cold_open_validates_structure():
    """Cold open requires all fields."""
    cold_open = ColdOpen(
        complaint_line="Sam, I swear if that generator fails one more time",
        realization="Oh shit. Oh.",
        intro_sentence_1="This is Maya Rodriguez with Field Reports.",
        intro_sentence_2="Broadcasting from the ruins of Sector 7."
    )

    assert cold_open.complaint_line is not None
    assert cold_open.realization is not None
    assert cold_open.intro_sentence_1 is not None
    assert cold_open.intro_sentence_2 is not None


def test_interview_segment_has_interference_flag():
    """Interview segment tracks whether interference follows."""
    segment = InterviewSegment(
        question="What kind of organizing work are you doing?",
        answer="We're setting up mesh networks for free communication.",
        interference_after=True
    )

    assert segment.interference_after is True


def test_field_report_script_validates_min_segments():
    """Field report requires 4-6 interview segments."""
    with pytest.raises(ValueError, match="at least 4 interview segments"):
        FieldReportScript(
            cold_open=ColdOpen(
                complaint_line="test",
                realization="test",
                intro_sentence_1="test",
                intro_sentence_2="test"
            ),
            interview_segments=[],  # Too few
            signoff="Stay safe out there."
        )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ai_radio/models/test_script_schema.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.models.script_schema'"

**Step 3: Write minimal implementation**

```python
# src/ai_radio/models/script_schema.py
"""Pydantic models for structured field report scripts."""
from pydantic import BaseModel, Field, model_validator


class ColdOpen(BaseModel):
    """Cold open with complaint, realization, and intro."""
    complaint_line: str = Field(..., description="Whispered complaint about equipment/patrol (~15 words)")
    realization: str = Field(..., description="Shocked realization mic is live")
    intro_sentence_1: str = Field(..., description="First introduction sentence")
    intro_sentence_2: str = Field(..., description="Second introduction sentence")


class InterviewSegment(BaseModel):
    """Single question/answer exchange in interview."""
    question: str = Field(..., description="Presenter question (~25-30 words)")
    answer: str = Field(..., description="Source answer (~40-50 words)")
    interference_after: bool = Field(default=False, description="Whether interference follows this segment")


class FieldReportScript(BaseModel):
    """Complete field report structure."""
    cold_open: ColdOpen
    interview_segments: list[InterviewSegment] = Field(..., min_length=4, max_length=6)
    signoff: str = Field(..., description="Final signoff line")

    @model_validator(mode='after')
    def validate_segment_count(self):
        """Ensure 4-6 interview segments."""
        if not (4 <= len(self.interview_segments) <= 6):
            raise ValueError(f"Must have 4-6 interview segments, got {len(self.interview_segments)}")
        return self
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ai_radio/models/test_script_schema.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ai_radio/models/script_schema.py tests/ai_radio/models/test_script_schema.py
git commit -m "feat: add Pydantic models for structured field report scripts"
```

---

## Task 2: Implement JSON Schema Generator

**Files:**
- Modify: `scripts/test_cold_open.py:23-128`
- Test: `tests/scripts/test_json_generation.py`

**Step 1: Write the failing test**

```python
# tests/scripts/test_json_generation.py
"""Tests for JSON schema based script generation."""
import json
from scripts.test_cold_open import generate_field_report_json
from ai_radio.models.script_schema import FieldReportScript


def test_generate_field_report_json_returns_valid_structure():
    """JSON generation returns valid FieldReportScript."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = [
        "Bridgeport Mutual Aid - solar chargers",
        "West Side Watchdogs - community defense"
    ]

    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)

    # Should parse as valid FieldReportScript
    script = FieldReportScript(**data)

    assert script.cold_open is not None
    assert len(script.interview_segments) >= 4
    assert len(script.interview_segments) <= 6
    assert script.signoff is not None


def test_first_segment_has_interference():
    """First interview segment should have interference_after=True."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = ["Test topic"]

    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    assert script.interview_segments[0].interference_after is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/scripts/test_json_generation.py -v`
Expected: FAIL with "ImportError: cannot import name 'generate_field_report_json'"

**Step 3: Write minimal implementation**

```python
# scripts/test_cold_open.py (replace generate_cold_open_with_field_report function)

def generate_field_report_json(
    presenter_name: str,
    source_name: str,
    topics: list
) -> str:
    """Generate field report as structured JSON using schema.

    Args:
        presenter_name: Name of the field reporter
        source_name: Name of the interview source
        topics: List of resistance group topics to cover

    Returns:
        JSON string matching FieldReportScript schema
    """
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    topics_text = '\n'.join([f"- {topic}" for topic in topics])

    prompt = f"""Generate a pirate radio field report as structured JSON.

WORLD CONTEXT:
{config.world.world_setting}

SPEAKERS:
- {presenter_name} (field reporter for resistance radio)
- {source_name} (organizer from resistance movement)

TOPICS:
{topics_text}

STRUCTURE REQUIREMENTS:

**cold_open** (4 fields):
- complaint_line: {presenter_name} whispers complaint about equipment/patrol (~15 words)
- realization: Shocked reaction to mic being live (e.g., "Oh shit. Oh.")
- intro_sentence_1: First introduction in normal voice (~20 words)
- intro_sentence_2: Second introduction continuing setup (~20 words)

**interview_segments** (4-6 items, each with 3 fields):
- question: {presenter_name} asks about organizing work (~25-30 words)
- answer: {source_name} responds about their work (~40-50 words)
- interference_after: Boolean - true for segments 0 and 2 (first and third Q&A)

**signoff**: {presenter_name} signs off (~15-20 words)

WORD BUDGETS (strict):
- Total cold_open: ~70 words
- Each interview segment: ~70-80 words
- Total script: 700-900 words (4-6 segments × 75 words average = 300-450 words + cold open + signoff)

CRITICAL: Set interference_after=true ONLY on segments 0 and 2. This places interference IMMEDIATELY after first answer and third answer.

OUTPUT: Valid JSON matching this exact structure:
{{{{
  "cold_open": {{{{
    "complaint_line": "...",
    "realization": "...",
    "intro_sentence_1": "...",
    "intro_sentence_2": "..."
  }}}},
  "interview_segments": [
    {{{{
      "question": "...",
      "answer": "...",
      "interference_after": true
    }}}},
    ...
  ],
  "signoff": "..."
}}}}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json"
        )
    )

    return response.text
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/scripts/test_json_generation.py -v`
Expected: PASS (2 tests) - may take 10-20 seconds for LLM calls

**Step 5: Commit**

```bash
git add scripts/test_cold_open.py tests/scripts/test_json_generation.py
git commit -m "feat: implement JSON schema based script generation"
```

---

## Task 3: Implement Validation Logic

**Files:**
- Create: `src/ai_radio/script_validation.py`
- Test: `tests/ai_radio/test_script_validation.py`

**Step 1: Write the failing test**

```python
# tests/ai_radio/test_script_validation.py
"""Tests for script validation logic."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_validation import validate_script, ValidationIssue


def test_validate_script_passes_good_structure():
    """Valid script passes all checks."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Sam I swear if that generator fails",  # 7 words - OK
            realization="Oh shit",
            intro_sentence_1="This is Maya Rodriguez with Field Reports",  # 7 words - OK
            intro_sentence_2="Broadcasting from the ruins of Sector Seven"  # 7 words - OK
        ),
        interview_segments=[
            InterviewSegment(
                question="What organizing work are you doing?",  # 6 words - OK
                answer="We are setting up mesh networks for free communication in the neighborhood.",  # 13 words - OK
                interference_after=True
            ),
            InterviewSegment(
                question="What challenges do you face?",
                answer="Corporate security patrols are a constant threat to our operations.",
                interference_after=False
            ),
            InterviewSegment(
                question="How can people help?",
                answer="Join your local mutual aid network and share technical skills.",
                interference_after=True
            ),
            InterviewSegment(
                question="What is your message?",
                answer="Solidarity across neighborhoods is how we build resilient communities.",
                interference_after=False
            )
        ],
        signoff="Stay safe out there"
    )

    issues = validate_script(script)
    assert len(issues) == 0


def test_validate_script_catches_long_cold_open():
    """Validation catches cold open complaint over 25 words."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Sam I swear if that generator fails one more time I am going to lose my mind this is ridiculous we have been dealing with this for weeks",  # 28 words - TOO LONG
            realization="Oh shit",
            intro_sentence_1="This is Maya",
            intro_sentence_2="Broadcasting from ruins"
        ),
        interview_segments=[
            InterviewSegment(question="q", answer="a", interference_after=True),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a")
        ],
        signoff="Stay safe"
    )

    issues = validate_script(script)
    assert len(issues) > 0
    assert any("cold_open.complaint_line" in issue.field for issue in issues)
    assert any("25 words" in issue.message for issue in issues)


def test_validate_script_requires_first_interference():
    """Validation requires interference after first segment."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test",
            intro_sentence_2="Test"
        ),
        interview_segments=[
            InterviewSegment(question="q", answer="a", interference_after=False),  # WRONG - should be True
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a")
        ],
        signoff="Stay safe"
    )

    issues = validate_script(script)
    assert len(issues) > 0
    assert any("interview_segments[0]" in issue.field for issue in issues)
    assert any("interference" in issue.message.lower() for issue in issues)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ai_radio/test_script_validation.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.script_validation'"

**Step 3: Write minimal implementation**

```python
# src/ai_radio/script_validation.py
"""Validation logic for field report scripts."""
from dataclasses import dataclass
from ai_radio.models.script_schema import FieldReportScript


@dataclass
class ValidationIssue:
    """A validation issue found in the script."""
    field: str
    message: str
    severity: str = "error"  # error, warning


def validate_script(script: FieldReportScript) -> list[ValidationIssue]:
    """Validate script structure and constraints.

    Args:
        script: The field report script to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    # Validate cold open word counts
    complaint_words = len(script.cold_open.complaint_line.split())
    if complaint_words > 25:
        issues.append(ValidationIssue(
            field="cold_open.complaint_line",
            message=f"Complaint line too long: {complaint_words} words (max 25 words)"
        ))

    intro1_words = len(script.cold_open.intro_sentence_1.split())
    if intro1_words > 30:
        issues.append(ValidationIssue(
            field="cold_open.intro_sentence_1",
            message=f"Intro sentence 1 too long: {intro1_words} words (max 30 words)"
        ))

    intro2_words = len(script.cold_open.intro_sentence_2.split())
    if intro2_words > 30:
        issues.append(ValidationIssue(
            field="cold_open.intro_sentence_2",
            message=f"Intro sentence 2 too long: {intro2_words} words (max 30 words)"
        ))

    # Validate interview segments
    for i, segment in enumerate(script.interview_segments):
        question_words = len(segment.question.split())
        if question_words > 40:
            issues.append(ValidationIssue(
                field=f"interview_segments[{i}].question",
                message=f"Question too long: {question_words} words (max 40 words)"
            ))

        answer_words = len(segment.answer.split())
        if answer_words > 60:
            issues.append(ValidationIssue(
                field=f"interview_segments[{i}].answer",
                message=f"Answer too long: {answer_words} words (max 60 words)"
            ))

    # Validate interference placement
    if script.interview_segments:
        if not script.interview_segments[0].interference_after:
            issues.append(ValidationIssue(
                field="interview_segments[0].interference_after",
                message="First segment must have interference_after=True"
            ))

    # Validate total word count
    total_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split()) +
        sum(len(s.question.split()) + len(s.answer.split()) for s in script.interview_segments) +
        len(script.signoff.split())
    )

    if total_words > 1000:
        issues.append(ValidationIssue(
            field="total_word_count",
            message=f"Script too long: {total_words} words (max 1000 words)",
            severity="warning"
        ))

    return issues
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ai_radio/test_script_validation.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ai_radio/script_validation.py tests/ai_radio/test_script_validation.py
git commit -m "feat: add validation logic for field report scripts"
```

---

## Task 4: Implement Repair Logic

**Files:**
- Create: `src/ai_radio/script_repair.py`
- Test: `tests/ai_radio/test_script_repair.py`

**Step 1: Write the failing test**

```python
# tests/ai_radio/test_script_repair.py
"""Tests for script repair logic."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_repair import repair_script
from ai_radio.script_validation import validate_script


def test_repair_script_fixes_missing_first_interference():
    """Repair ensures first segment has interference_after=True."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test",
            intro_sentence_2="Test"
        ),
        interview_segments=[
            InterviewSegment(question="q1", answer="a1", interference_after=False),  # WRONG
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False)
        ],
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Should fix first segment
    assert repaired.interview_segments[0].interference_after is True

    # Should not break validation
    issues = validate_script(repaired)
    interference_issues = [i for i in issues if "interference" in i.message.lower()]
    assert len(interference_issues) == 0


def test_repair_script_adds_second_interference_if_enough_segments():
    """Repair adds second interference on segment 2 if present."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test",
            intro_sentence_2="Test"
        ),
        interview_segments=[
            InterviewSegment(question="q1", answer="a1", interference_after=True),
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False),
            InterviewSegment(question="q5", answer="a5", interference_after=False)
        ],
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Should ensure segment 2 has interference
    assert repaired.interview_segments[2].interference_after is True


def test_repair_script_preserves_content():
    """Repair does not modify question/answer content."""
    original_question = "What organizing work are you doing in the community?"
    original_answer = "We are building solidarity networks across neighborhoods."

    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test",
            intro_sentence_2="Test"
        ),
        interview_segments=[
            InterviewSegment(
                question=original_question,
                answer=original_answer,
                interference_after=False
            ),
            InterviewSegment(question="q2", answer="a2"),
            InterviewSegment(question="q3", answer="a3"),
            InterviewSegment(question="q4", answer="a4")
        ],
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Content should be unchanged
    assert repaired.interview_segments[0].question == original_question
    assert repaired.interview_segments[0].answer == original_answer
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ai_radio/test_script_repair.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.script_repair'"

**Step 3: Write minimal implementation**

```python
# src/ai_radio/script_repair.py
"""Repair logic for fixing common script violations."""
import logging
from ai_radio.models.script_schema import FieldReportScript


logger = logging.getLogger(__name__)


def repair_script(script: FieldReportScript) -> FieldReportScript:
    """Apply automatic repairs to common violations.

    Args:
        script: The script to repair

    Returns:
        Repaired script (new instance, original unchanged)
    """
    # Create mutable copy of segments
    repaired_segments = [s.model_copy() for s in script.interview_segments]

    # Fix: First segment MUST have interference
    if repaired_segments and not repaired_segments[0].interference_after:
        logger.info("Repair: Setting interference_after=True on first segment")
        repaired_segments[0].interference_after = True

    # Fix: Add second interference on segment 2 if we have 5+ segments
    if len(repaired_segments) >= 5 and not repaired_segments[2].interference_after:
        logger.info("Repair: Setting interference_after=True on third segment")
        repaired_segments[2].interference_after = True

    # Return new FieldReportScript with repaired segments
    return FieldReportScript(
        cold_open=script.cold_open.model_copy(),
        interview_segments=repaired_segments,
        signoff=script.signoff
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ai_radio/test_script_repair.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ai_radio/script_repair.py tests/ai_radio/test_script_repair.py
git commit -m "feat: add repair logic for script violations"
```

---

## Task 5: Implement Script Renderer with Programmatic Interference

**Files:**
- Create: `src/ai_radio/script_renderer.py`
- Test: `tests/ai_radio/test_script_renderer.py`

**Step 1: Write the failing test**

```python
# tests/ai_radio/test_script_renderer.py
"""Tests for script rendering with programmatic interference."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_renderer import render_script


def test_render_script_includes_cold_open():
    """Rendered script includes cold open with whisper tags."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Sam that generator is driving me crazy",
            realization="Oh shit",
            intro_sentence_1="This is Maya Rodriguez",
            intro_sentence_2="Broadcasting from Sector Seven"
        ),
        interview_segments=[
            InterviewSegment(question="q", answer="a", interference_after=True),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a")
        ],
        signoff="Stay safe"
    )

    rendered = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    # Cold open should have whispering tag on complaint
    assert "[whispering]" in rendered
    assert "Sam that generator is driving me crazy" in rendered

    # Realization should have shocked tag
    assert "[shocked]" in rendered
    assert "Oh shit" in rendered

    # Intro should NOT have whispering
    lines = rendered.split('\n')
    intro_lines = [l for l in lines if "This is Maya Rodriguez" in l]
    assert len(intro_lines) > 0
    assert "[whispering]" not in intro_lines[0]


def test_render_script_injects_interference_templates():
    """Renderer injects interference acknowledgments programmatically."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test",
            intro_sentence_2="Test"
        ),
        interview_segments=[
            InterviewSegment(
                question="What organizing work are you doing?",
                answer="We are building networks",
                interference_after=True
            ),
            InterviewSegment(
                question="What challenges?",
                answer="Corporate patrols",
                interference_after=False
            ),
            InterviewSegment(
                question="How to help?",
                answer="Join mutual aid",
                interference_after=True
            ),
            InterviewSegment(
                question="Your message?",
                answer="Solidarity",
                interference_after=False
            )
        ],
        signoff="Stay safe"
    )

    rendered = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    # Should have interference phrases (templates, not from model)
    interference_phrases = [
        "Sorry about that",
        "signal's spotty",
        "corp jammers",
        "signal's back"
    ]

    # At least one interference phrase should appear
    has_interference = any(phrase in rendered.lower() for phrase in interference_phrases)
    assert has_interference, f"No interference phrases found in:\n{rendered}"


def test_render_script_formats_with_speaker_tags():
    """Rendered script uses [speaker: Name] format."""
    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test complaint",
            realization="Oh no",
            intro_sentence_1="Intro one",
            intro_sentence_2="Intro two"
        ),
        interview_segments=[
            InterviewSegment(
                question="What is your work?",
                answer="We organize communities",
                interference_after=False
            ),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a")
        ],
        signoff="Stay safe everyone"
    )

    rendered = render_script(
        script,
        presenter="Maya Rodriguez",
        source="Sam Chen"
    )

    # Should have speaker tags
    assert "[speaker: Maya Rodriguez]" in rendered
    assert "[speaker: Sam Chen]" in rendered

    # Question should be from presenter
    assert "What is your work?" in rendered
    question_line = [l for l in rendered.split('\n') if "What is your work?" in l][0]
    assert "[speaker: Maya Rodriguez]" in question_line

    # Answer should be from source
    assert "We organize communities" in rendered
    answer_line = [l for l in rendered.split('\n') if "We organize communities" in l][0]
    assert "[speaker: Sam Chen]" in answer_line
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ai_radio/test_script_renderer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.script_renderer'"

**Step 3: Write minimal implementation**

```python
# src/ai_radio/script_renderer.py
"""Render structured scripts to final text format with programmatic interference."""
import random
from ai_radio.models.script_schema import FieldReportScript


# Template phrases for interference acknowledgments (NOT model-generated)
INTERFERENCE_TEMPLATES = [
    "[nervous] Sorry about that, someone's trying to jam us again...",
    "[frustrated] Damn corp jammers... [short pause] where was I?",
    "[worried] Can you still hear me? Signal's spotty...",
    "[annoyed] Hold on... [short pause] okay, signal's back",
    "[tense] They're trying to block us... [short pause] still here",
    "[defiant] Nice try, corps. [short pause] You can't silence us."
]


def render_script(
    script: FieldReportScript,
    presenter: str,
    source: str
) -> str:
    """Render structured script to final text format with speaker tags.

    Programmatically injects interference acknowledgments from templates
    rather than relying on model generation.

    Args:
        script: The structured script to render
        presenter: Name of the presenter/reporter
        source: Name of the interview source

    Returns:
        Formatted script text with speaker tags and interference
    """
    lines = []

    # Render cold open
    lines.append(
        f"[speaker: {presenter}] [whispering] [annoyed] "
        f"{script.cold_open.complaint_line}"
    )
    lines.append(
        f"[speaker: {presenter}] [shocked] "
        f"{script.cold_open.realization}"
    )
    lines.append(
        f"[speaker: {presenter}] [embarrassed] [sigh] "
        f"{script.cold_open.intro_sentence_1}"
    )
    lines.append(
        f"[speaker: {presenter}] [confident] "
        f"{script.cold_open.intro_sentence_2}"
    )

    # Render interview segments with programmatic interference injection
    for segment in script.interview_segments:
        # Question from presenter
        lines.append(f"[speaker: {presenter}] {segment.question}")

        # Answer from source
        lines.append(f"[speaker: {source}] [earnest] {segment.answer}")

        # Inject interference acknowledgment if flagged
        if segment.interference_after:
            interference_phrase = random.choice(INTERFERENCE_TEMPLATES)
            lines.append(f"[speaker: {presenter}] {interference_phrase}")

    # Render signoff
    lines.append(f"[speaker: {presenter}] [determined] {script.signoff}")

    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ai_radio/test_script_renderer.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/ai_radio/script_renderer.py tests/ai_radio/test_script_renderer.py
git commit -m "feat: add script renderer with programmatic interference injection"
```

---

## Task 6: Integrate with test_cold_open.py

**Files:**
- Modify: `scripts/test_cold_open.py:129-189`

**Step 1: Write integration test**

```python
# Add to bottom of scripts/test_cold_open.py before if __name__ == "__main__":

def test_json_workflow_end_to_end():
    """Test complete JSON workflow: generate → validate → repair → render."""
    from ai_radio.models.script_schema import FieldReportScript
    from ai_radio.script_validation import validate_script
    from ai_radio.script_repair import repair_script
    from ai_radio.script_renderer import render_script

    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = ["Test organizing work"]

    # Generate JSON
    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    # Validate
    issues = validate_script(script)

    # Repair if needed
    if issues:
        script = repair_script(script)

    # Render to final format
    final_script = render_script(script, presenter, source)

    # Verify structure
    assert "[speaker: Maya Rodriguez]" in final_script
    assert "[speaker: Sam Chen]" in final_script
    assert "[whispering]" in final_script  # Cold open

    # Verify interference templates injected
    has_interference = any(
        phrase in final_script.lower()
        for phrase in ["sorry about", "jammers", "signal"]
    )
    assert has_interference

    print("✅ End-to-end JSON workflow successful")
    return final_script
```

**Step 2: Run test**

Run: `cd scripts && python -c "from test_cold_open import test_json_workflow_end_to_end; test_json_workflow_end_to_end()"`
Expected: Output "✅ End-to-end JSON workflow successful"

**Step 3: Update main() to use new workflow**

```python
# scripts/test_cold_open.py - replace main() function

def main():
    """Generate and synthesize field report using JSON schema workflow."""
    import json
    from ai_radio.models.script_schema import FieldReportScript
    from ai_radio.script_validation import validate_script
    from ai_radio.script_repair import repair_script
    from ai_radio.script_renderer import render_script

    presenter_name = "Maya Rodriguez"
    source_name = "Sam Chen"

    # Sample resistance topics
    topics = [
        "The Bridgeport Mutual Aid Collective - distributing solar chargers and water filters",
        "West Side Watchdogs - community defense patrols against corporate security",
        "Pilsen Solidarity Network - setting up mesh networks for free communication"
    ]

    print("🎬 Generating Field Report with JSON Schema Workflow")
    print(f"   Presenter: {presenter_name}")
    print(f"   Source: {source_name}")
    print()

    # Step 1: Generate structured JSON
    print("✍️  Generating structured JSON with schema...")
    json_output = generate_field_report_json(presenter_name, source_name, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)
    print(f"   ✅ Valid JSON structure generated")
    print()

    # Step 2: Validate structure
    print("🔍 Validating structure...")
    issues = validate_script(script)
    if issues:
        print(f"   ⚠️  Found {len(issues)} validation issues:")
        for issue in issues:
            print(f"      - {issue.field}: {issue.message}")
    else:
        print(f"   ✅ No validation issues")
    print()

    # Step 3: Repair if needed
    if issues:
        print("🔧 Repairing violations...")
        script = repair_script(script)
        print(f"   ✅ Repairs applied")
        print()

    # Step 4: Render to final script
    print("📝 Rendering final script with programmatic interference...")
    final_script = render_script(script, presenter_name, source_name)

    word_count = len(final_script.split())
    print(f"   Script length: {len(final_script)} characters")
    print(f"   Word count: {word_count} words")
    print()
    print("=" * 60)
    print(final_script)
    print("=" * 60)
    print()

    # Step 5: Synthesize with two speakers and background bed
    print("🔊 Synthesizing audio with background bed...")
    output_path = Path(f"/tmp/field-report-json-{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")

    personas = [
        {"name": presenter_name, "traits": "female field reporter"},
        {"name": source_name, "traits": "male organizer from resistance"}
    ]

    audio_file = synthesize_show_audio(
        script_text=final_script,
        personas=personas,
        output_path=output_path,
        add_bed=True  # Add background bed with ducking
    )

    print()
    print(f"✅ Field report generated: {output_path}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Voices: {audio_file.voice}")
    print()
    print("🎯 JSON Schema Workflow Benefits:")
    print("  ✓ Reliable cold open timing (enforced by schema)")
    print("  ✓ Programmatic interference injection (templates)")
    print("  ✓ Word budget constraints (validated)")
    print("  ✓ Structural guarantees (Pydantic models)")
    print()
    print("📊 Metrics:")
    print(f"  - Total words: {word_count}")
    print(f"  - Cold open: ~{len(script.cold_open.complaint_line.split()) + len(script.cold_open.intro_sentence_1.split()) + len(script.cold_open.intro_sentence_2.split())} words")
    print(f"  - Interview segments: {len(script.interview_segments)}")
    print(f"  - Duration estimate: {audio_file.duration_estimate:.1f}s (~{audio_file.duration_estimate/60:.1f} min)")

    return 0
```

**Step 4: Run full test**

Run: `cd scripts && python test_cold_open.py`
Expected:
- JSON generation succeeds
- Validation passes (or finds minor issues)
- Repair fixes issues
- Rendering produces script with interference
- Audio synthesis works
- Metrics printed

**Step 5: Commit**

```bash
git add scripts/test_cold_open.py
git commit -m "feat: integrate JSON schema workflow into test_cold_open.py"
```

---

## Task 7: Add Word Count Enforcement (Generator + Editor)

**Files:**
- Create: `src/ai_radio/script_editor.py`
- Test: `tests/ai_radio/test_script_editor.py`

**Step 1: Write the failing test**

```python
# tests/ai_radio/test_script_editor.py
"""Tests for script editor (word count enforcement)."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_editor import compress_script_to_budget


def test_compress_script_reduces_word_count():
    """Compressor reduces total word count while preserving structure."""
    # Create overlong script (simulated)
    long_answer = "This is a very long answer that goes on and on with many extra words that could be compressed to make it more concise and fit within the target word budget for the segment."

    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test intro",
            intro_sentence_2="Test intro two"
        ),
        interview_segments=[
            InterviewSegment(question="Short q?", answer=long_answer, interference_after=True),
            InterviewSegment(question="q2", answer=long_answer),
            InterviewSegment(question="q3", answer=long_answer),
            InterviewSegment(question="q4", answer=long_answer)
        ],
        signoff="Stay safe"
    )

    # Target: 100 words (should compress answers)
    compressed = compress_script_to_budget(script, target_words=100)

    # Word count should be closer to target
    original_words = sum(len(s.answer.split()) for s in script.interview_segments)
    compressed_words = sum(len(s.answer.split()) for s in compressed.interview_segments)

    assert compressed_words < original_words


def test_compress_script_preserves_cold_open():
    """Compressor does NOT modify cold open."""
    original_complaint = "Sam I swear that generator"

    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line=original_complaint,
            realization="Oh shit",
            intro_sentence_1="This is Maya",
            intro_sentence_2="Broadcasting from ruins"
        ),
        interview_segments=[
            InterviewSegment(
                question="q" * 50,  # Long
                answer="a" * 100,   # Long
                interference_after=True
            ),
            InterviewSegment(question="q", answer="a" * 100),
            InterviewSegment(question="q", answer="a" * 100),
            InterviewSegment(question="q", answer="a" * 100)
        ],
        signoff="Stay safe"
    )

    compressed = compress_script_to_budget(script, target_words=200)

    # Cold open should be unchanged
    assert compressed.cold_open.complaint_line == original_complaint
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ai_radio/test_script_editor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.script_editor'"

**Step 3: Write minimal implementation**

```python
# src/ai_radio/script_editor.py
"""Script editor for word count enforcement via compression."""
import logging
from ai_radio.models.script_schema import FieldReportScript, InterviewSegment
from ai_radio.config import config
import google.genai as genai


logger = logging.getLogger(__name__)


def compress_script_to_budget(
    script: FieldReportScript,
    target_words: int
) -> FieldReportScript:
    """Compress script to fit word budget by shortening answers.

    Uses LLM editor to make surgical edits only to answers,
    preserving cold open, questions, and structure.

    Args:
        script: The script to compress
        target_words: Target total word count

    Returns:
        Compressed script at or near target
    """
    # Calculate current word count
    current_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split()) +
        sum(
            len(s.question.split()) + len(s.answer.split())
            for s in script.interview_segments
        ) +
        len(script.signoff.split())
    )

    if current_words <= target_words:
        logger.info(f"Script already at budget: {current_words} <= {target_words}")
        return script

    # Calculate how much to reduce
    words_to_cut = current_words - target_words
    reduction_pct = (words_to_cut / current_words) * 100

    logger.info(
        f"Compressing script: {current_words} → {target_words} words "
        f"({reduction_pct:.1f}% reduction)"
    )

    # Build prompt for editor
    answers_text = "\n\n".join([
        f"ANSWER {i+1}:\n{seg.answer}"
        for i, seg in enumerate(script.interview_segments)
    ])

    prompt = f"""Edit these interview answers to reduce total length by {reduction_pct:.0f}%.

TARGET: Cut approximately {words_to_cut} words total

RULES:
- Make answers more concise while preserving key information
- Maintain natural speaking tone
- Keep answers substantial (not too terse)
- Distribute cuts across all answers proportionally

ANSWERS TO COMPRESS:

{answers_text}

OUTPUT: Return ONLY the compressed answers in the same format:

ANSWER 1:
[compressed answer 1]

ANSWER 2:
[compressed answer 2]

etc."""

    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=genai.types.GenerateContentConfig(temperature=0.0)
    )

    # Parse compressed answers
    compressed_answers = []
    current_answer = []

    for line in response.text.split('\n'):
        if line.strip().startswith("ANSWER"):
            if current_answer:
                compressed_answers.append('\n'.join(current_answer).strip())
                current_answer = []
        else:
            if line.strip():
                current_answer.append(line)

    if current_answer:
        compressed_answers.append('\n'.join(current_answer).strip())

    # Build new segments with compressed answers
    new_segments = []
    for i, segment in enumerate(script.interview_segments):
        if i < len(compressed_answers):
            new_segments.append(
                InterviewSegment(
                    question=segment.question,
                    answer=compressed_answers[i],
                    interference_after=segment.interference_after
                )
            )
        else:
            new_segments.append(segment)

    # Return new script with compressed segments
    return FieldReportScript(
        cold_open=script.cold_open.model_copy(),
        interview_segments=new_segments,
        signoff=script.signoff
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ai_radio/test_script_editor.py -v`
Expected: PASS (2 tests) - may take 10-20 seconds for LLM calls

**Step 5: Commit**

```bash
git add src/ai_radio/script_editor.py tests/ai_radio/test_script_editor.py
git commit -m "feat: add script editor for word count enforcement"
```

---

## Task 8: Integration Test with Full Audio Pipeline

**Files:**
- Test: `tests/integration/test_json_workflow_with_audio.py`

**Step 1: Write integration test**

```python
# tests/integration/test_json_workflow_with_audio.py
"""Integration test for complete JSON workflow with audio generation."""
import json
from pathlib import Path
import pytest
from scripts.test_cold_open import generate_field_report_json
from ai_radio.models.script_schema import FieldReportScript
from ai_radio.script_validation import validate_script
from ai_radio.script_repair import repair_script
from ai_radio.script_renderer import render_script
from ai_radio.script_editor import compress_script_to_budget
from ai_radio.show_generator import synthesize_show_audio


@pytest.mark.integration
def test_complete_json_workflow_with_audio():
    """Test complete workflow: JSON → validate → repair → compress → render → audio."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = [
        "Bridgeport Mutual Aid - solar chargers",
        "West Side Watchdogs - community defense"
    ]

    # Step 1: Generate JSON
    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    assert script.cold_open is not None
    assert len(script.interview_segments) >= 4

    # Step 2: Validate
    issues = validate_script(script)

    # Step 3: Repair if needed
    if issues:
        script = repair_script(script)

    # Step 4: Compress if over budget
    script = compress_script_to_budget(script, target_words=900)

    # Step 5: Render
    final_script = render_script(script, presenter, source)

    # Verify structure
    assert "[speaker: Maya Rodriguez]" in final_script
    assert "[whispering]" in final_script
    assert any(phrase in final_script.lower() for phrase in ["sorry", "jammers", "signal"])

    # Step 6: Synthesize audio
    output_path = Path("/tmp/test-json-workflow-integration.mp3")
    personas = [
        {"name": presenter, "traits": "female field reporter"},
        {"name": source, "traits": "male organizer"}
    ]

    audio_file = synthesize_show_audio(
        script_text=final_script,
        personas=personas,
        output_path=output_path,
        add_bed=True
    )

    # Verify audio was generated
    assert output_path.exists()
    assert audio_file.duration_estimate > 0

    # Verify timing constraints
    # Cold open should be roughly 15-25 seconds (using ~150 words/min speaking rate)
    cold_open_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split())
    )
    cold_open_seconds = (cold_open_words / 150) * 60  # Rough estimate

    assert 10 <= cold_open_seconds <= 30, f"Cold open timing off: {cold_open_seconds}s"

    # Total duration should be reasonable for word count
    total_words = len(final_script.split())
    expected_duration = (total_words / 150) * 60  # ~150 wpm

    # Allow 50% variance for pauses, emotion tags, etc.
    assert expected_duration * 0.5 <= audio_file.duration_estimate <= expected_duration * 1.5

    print(f"✅ Integration test passed")
    print(f"   Words: {total_words}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Cold open: ~{cold_open_seconds:.1f}s")
    print(f"   Output: {output_path}")
```

**Step 2: Run integration test**

Run: `pytest tests/integration/test_json_workflow_with_audio.py -v -m integration`
Expected: PASS - takes ~30-60 seconds for full workflow

**Step 3: Commit**

```bash
git add tests/integration/test_json_workflow_with_audio.py
git commit -m "test: add integration test for complete JSON workflow with audio"
```

---

## Task 9: Documentation and Metrics

**Files:**
- Create: `docs/json-schema-workflow.md`

**Step 1: Write documentation**

```markdown
# docs/json-schema-workflow.md

# JSON Schema Script Generation Workflow

## Overview

Replaces single-pass prompt engineering with structured JSON generation + programmatic rendering to reliably enforce timing and structure constraints.

## Problem

Single-pass prompting cannot enforce global constraints (word count, timing, placement) because:
- LLMs generate token-by-token, optimizing for local plausibility
- Cannot retroactively satisfy constraints after generation
- "Step 6: Verify Word Count" runs AFTER all tokens are already generated
- Self-verification is inherently weak

**Expert consensus (GPT-5.2, Gemini-3-Pro, 9/10 confidence):** Architectural changes required.

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ 1. JSON Schema Generation                                   │
│    - Gemini 2.0 Flash with response_mime_type="json"        │
│    - Per-segment word budgets                               │
│    - Explicit interference_after flags                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Validation (Programmatic)                                │
│    - Check word counts per segment                          │
│    - Verify interference placement                          │
│    - Validate segment count (4-6)                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Repair (Surgical)                                        │
│    - Fix missing interference flags                         │
│    - Preserve all content (no regeneration)                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Compression (If Needed)                                  │
│    - LLM editor for targeted answer reduction               │
│    - Preserve cold open, questions, structure               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Rendering (Deterministic)                                │
│    - Add speaker tags                                       │
│    - Inject interference from templates (NOT model)         │
│    - Add emotion tags                                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Audio Synthesis                                          │
│    - TTS with Gemini                                        │
│    - Background beds with ducking                           │
│    - Pirate radio effects                                   │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Pydantic Models (`script_schema.py`)

```python
class ColdOpen(BaseModel):
    complaint_line: str  # ~15 words
    realization: str     # "[shocked] Oh shit"
    intro_sentence_1: str  # ~20 words
    intro_sentence_2: str  # ~20 words

class InterviewSegment(BaseModel):
    question: str  # ~25-30 words
    answer: str    # ~40-50 words
    interference_after: bool  # Explicit flag

class FieldReportScript(BaseModel):
    cold_open: ColdOpen
    interview_segments: list[InterviewSegment]  # 4-6 items
    signoff: str
```

### 2. Validation (`script_validation.py`)

Programmatic checks:
- Cold open complaint ≤ 25 words
- Each question ≤ 40 words
- Each answer ≤ 60 words
- First segment has `interference_after=True`
- Total word count ≤ 1000 words

Returns list of `ValidationIssue` objects.

### 3. Repair (`script_repair.py`)

Surgical fixes for common violations:
- Ensure first segment has interference
- Add second interference if 5+ segments
- **Preserves all content** (no regeneration)

### 4. Compression (`script_editor.py`)

Two-pass approach:
1. Generate (likely overlong)
2. LLM editor compresses answers only

Preserves:
- Cold open (untouched)
- Questions (untouched)
- Structure (interference flags, segment order)

### 5. Rendering (`script_renderer.py`)

Deterministic rendering:
- Speaker tags: `[speaker: Maya Rodriguez]`
- Emotion tags: `[whispering]`, `[shocked]`, `[earnest]`
- **Interference templates**: Injected from predefined list, NOT generated

Templates:
```python
INTERFERENCE_TEMPLATES = [
    "[nervous] Sorry about that, someone's trying to jam us again...",
    "[frustrated] Damn corp jammers... [short pause] where was I?",
    "[worried] Can you still hear me? Signal's spotty...",
    ...
]
```

## Usage

```python
from scripts.test_cold_open import generate_field_report_json
from ai_radio.models.script_schema import FieldReportScript
from ai_radio.script_validation import validate_script
from ai_radio.script_repair import repair_script
from ai_radio.script_renderer import render_script
from ai_radio.script_editor import compress_script_to_budget

# 1. Generate JSON
json_output = generate_field_report_json(presenter, source, topics)
script = FieldReportScript(**json.loads(json_output))

# 2. Validate
issues = validate_script(script)

# 3. Repair if needed
if issues:
    script = repair_script(script)

# 4. Compress if over budget
script = compress_script_to_budget(script, target_words=900)

# 5. Render to final format
final_script = render_script(script, presenter, source)

# 6. Synthesize audio (existing pipeline)
audio_file = synthesize_show_audio(
    script_text=final_script,
    personas=[...],
    output_path=output_path,
    add_bed=True
)
```

## Benefits vs. Prompt Engineering

| Prompt Engineering | JSON Schema Workflow |
|-------------------|---------------------|
| Soft constraints | Hard constraints (schema) |
| Model self-checks | Programmatic validation |
| "MUST" = preference | Schema = compiler error |
| Global drift | Per-segment budgets |
| Model writes interference | Templates (deterministic) |
| Single-pass generation | Multi-stage pipeline |
| Unreliable timing | Validated word budgets |

## Metrics

After implementation, track:
- Cold open duration (target: 15-25s)
- First interference timing (target: 30-70s)
- Total word count (target: 700-900)
- Validation issue frequency
- Repair success rate

## Testing

```bash
# Unit tests
pytest tests/ai_radio/models/test_script_schema.py
pytest tests/ai_radio/test_script_validation.py
pytest tests/ai_radio/test_script_repair.py
pytest tests/ai_radio/test_script_renderer.py
pytest tests/ai_radio/test_script_editor.py

# Integration test
pytest tests/integration/test_json_workflow_with_audio.py -m integration

# End-to-end test
python scripts/test_cold_open.py
```

## Future Enhancements

1. **Segment-level generation**: Generate each segment separately with stop sequences
2. **Validator → repair loop**: Iterative refinement until all constraints met
3. **Metrics dashboard**: Track constraint satisfaction rates over time
4. **A/B testing**: Compare prompt vs. schema approach on same topics
```

**Step 2: Commit documentation**

```bash
git add docs/json-schema-workflow.md
git commit -m "docs: add JSON schema workflow documentation"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-01-18-json-schema-script-generation.md`.

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
