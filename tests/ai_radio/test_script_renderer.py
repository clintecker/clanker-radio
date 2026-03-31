"""Tests for script rendering with programmatic interference."""
import pytest

from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_renderer import render_script


def _cold_open(**overrides):
    """Helper to create ColdOpen with defaults."""
    defaults = dict(
        complaint_line="Test",
        realization="Oh",
        intro_sentence_1="Test",
        intro_sentence_2="Test",
        guest_intro="Test guest intro",
    )
    defaults.update(overrides)
    return ColdOpen(**defaults)


def _make_segments(specs):
    """Create 8+ interview segments from a list of (q, a, interference) specs.

    Pads to 8 segments if fewer are provided.
    """
    segments = []
    for q, a, interference in specs:
        segments.append(InterviewSegment(
            question=q, answer=a, interference_after=interference
        ))
    while len(segments) < 8:
        segments.append(InterviewSegment(
            question=f"q_pad{len(segments)+1}",
            answer=f"a_pad{len(segments)+1}",
            interference_after=False,
        ))
    return segments


def test_render_script_returns_tuple_with_metadata():
    """Renderer returns (script_text, metadata) tuple."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("q1", "a1", False),
            ("q2", "a2", False),
            ("q3", "a3", False),
            ("q4", "a4", False),
        ]),
        signoff="Stay safe"
    )

    result = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    # Should return tuple
    assert isinstance(result, tuple)
    assert len(result) == 2

    script_text, metadata = result

    # Script text should be string
    assert isinstance(script_text, str)
    assert len(script_text) > 0

    # Metadata should be dict with required fields
    assert isinstance(metadata, dict)
    assert "acknowledgment_phrases" in metadata
    assert "total_lines" in metadata
    assert "total_words" in metadata

    # Metadata fields should have correct types
    assert isinstance(metadata["acknowledgment_phrases"], list)
    assert isinstance(metadata["total_lines"], int)
    assert isinstance(metadata["total_words"], int)


def test_render_script_includes_cold_open():
    """Rendered script includes cold open with whisper tags."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(
            complaint_line="Sam that generator is driving me crazy",
            realization="Oh shit",
            intro_sentence_1="This is Maya Rodriguez",
            intro_sentence_2="Broadcasting from Sector Seven",
        ),
        interview_segments=_make_segments([
            ("q", "a", True),
            ("q", "a", False),
            ("q", "a", False),
            ("q", "a", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

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
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("What organizing work are you doing?", "We are building networks", True),
            ("What challenges?", "Corporate patrols", False),
            ("How to help?", "Join mutual aid", True),
            ("Your message?", "Solidarity", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    # Should have interference phrases (templates, not from model)
    interference_phrases = [
        "Sorry about that, someone's trying to jam us again",
        "Damn corp jammers",
        "Can you still hear me? Signal's spotty",
        "okay, signal's back",
        "They're trying to block us",
        "You can't silence us"
    ]

    # At least one interference phrase should appear
    has_interference = any(phrase in rendered for phrase in interference_phrases)
    assert has_interference, f"No interference phrases found in:\n{rendered}"


def test_render_script_formats_with_speaker_tags():
    """Rendered script uses [speaker: Name] format."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(
            complaint_line="Test complaint",
            realization="Oh no",
            intro_sentence_1="Intro one",
            intro_sentence_2="Intro two",
        ),
        interview_segments=_make_segments([
            ("What is your work?", "We organize communities", False),
            ("q", "a", False),
            ("q", "a", False),
            ("q", "a", False),
        ]),
        signoff="Stay safe everyone"
    )

    rendered, metadata = render_script(
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


def test_render_script_adds_emotions_to_questions():
    """Questions get random emotions from emotion pool."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("Why are you organizing?", "For justice", False),
            ("What challenges do you face?", "Many", False),
            ("How can people help?", "Join us", False),
            ("Can you tell us more?", "Yes", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    question_emotions = [
        "curious", "concerned", "interested", "skeptical", "worried",
        "urgent", "intense", "direct", "probing", "careful"
    ]
    question_lines = [l for l in rendered.split('\n') if "Maya Rodriguez" in l and any(q in l for q in ["Why", "What", "How", "Can"])]

    for line in question_lines:
        has_emotion = any(f"[{emotion}]" in line for emotion in question_emotions)
        assert has_emotion, f"Question line missing emotion: {line}"


def test_render_script_adds_emotions_to_answers():
    """Answers get random emotions from emotion pool."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("Q1?", "We fight for our community", False),
            ("Q2?", "There is hope for change", False),
            ("Q3?", "We struggle every day", False),
            ("Q4?", "Together we are strong", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    answer_emotions = [
        "earnest", "passionate", "determined", "worried", "hopeful", "confident",
        "defiant", "resolute", "fierce", "steadfast", "grim", "intense"
    ]
    answer_lines = [l for l in rendered.split('\n') if "Sam Chen" in l and any(kw in l for kw in ["fight", "hope", "struggle", "Together"])]

    for line in answer_lines:
        has_emotion = any(f"[{emotion}]" in line for emotion in answer_emotions)
        assert has_emotion, f"Answer line missing emotion: {line}"


def test_render_script_tracks_acknowledgment_phrases():
    """Metadata includes acknowledgment phrases with line numbers."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("Q1?", "A1", True),
            ("Q2?", "A2", False),
            ("Q3?", "A3", True),
            ("Q4?", "A4", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    # Should have 2 acknowledgment phrases (matching interference_after=True count)
    assert len(metadata["acknowledgment_phrases"]) == 2

    for ack in metadata["acknowledgment_phrases"]:
        assert "line_num" in ack
        assert "phrase" in ack
        assert "timestamp" in ack

        assert isinstance(ack["line_num"], int)
        assert ack["line_num"] > 0

        assert isinstance(ack["phrase"], str)
        assert len(ack["phrase"]) > 0
        assert "[" not in ack["phrase"]
        assert "]" not in ack["phrase"]

        assert ack["timestamp"] is None


def test_render_script_phrase_metadata_matches_script_content():
    """Acknowledgment phrases in metadata appear in rendered script."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_make_segments([
            ("Q1?", "A1", True),
            ("Q2?", "A2", True),
            ("Q3?", "A3", False),
            ("Q4?", "A4", False),
        ]),
        signoff="Stay safe"
    )

    rendered, metadata = render_script(script, presenter="Maya Rodriguez", source="Sam Chen")

    for ack in metadata["acknowledgment_phrases"]:
        phrase = ack["phrase"]
        words = phrase.split()
        if len(words) >= 2:
            first_two = " ".join(words[0:2])
            assert first_two in rendered, f"Phrase '{phrase}' first words '{first_two}' not found in rendered script"
