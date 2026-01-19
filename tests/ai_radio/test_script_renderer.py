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
    # Check for all 6 template phrases to avoid flaky test failures
    # These phrases correspond to unique substrings from each template
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
