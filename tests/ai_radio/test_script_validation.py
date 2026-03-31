"""Tests for script validation logic."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_validation import validate_script, ValidationIssue


def _cold_open(**overrides):
    defaults = dict(
        complaint_line="Test",
        realization="Oh",
        intro_sentence_1="Test",
        intro_sentence_2="Test",
        guest_intro="Test guest intro",
    )
    defaults.update(overrides)
    return ColdOpen(**defaults)


def _pad_segments(segments, target=8):
    while len(segments) < target:
        segments.append(InterviewSegment(
            question=f"q_pad{len(segments)+1}",
            answer=f"a_pad{len(segments)+1}",
            interference_after=False,
        ))
    return segments


def test_validate_script_passes_good_structure():
    """Valid script passes all checks."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(
            complaint_line="Sam I swear if that generator fails",  # 7 words - OK
            realization="Oh shit",
            intro_sentence_1="This is Maya Rodriguez with Field Reports",  # 7 words - OK
            intro_sentence_2="Broadcasting from the ruins of Sector Seven",  # 7 words - OK
        ),
        interview_segments=_pad_segments([
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
            ),
        ]),
        signoff="Stay safe out there"
    )

    issues = validate_script(script)
    assert len(issues) == 0


def test_validate_script_catches_long_cold_open():
    """Validation catches cold open complaint over 25 words."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(
            complaint_line="Sam I swear if that generator fails one more time I am going to lose my mind this is ridiculous we have been dealing with this for weeks",  # 28 words - TOO LONG
            realization="Oh shit",
            intro_sentence_1="This is Maya",
            intro_sentence_2="Broadcasting from ruins",
        ),
        interview_segments=_pad_segments([
            InterviewSegment(question="q", answer="a", interference_after=True),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
        ]),
        signoff="Stay safe"
    )

    issues = validate_script(script)
    assert len(issues) > 0
    assert any("cold_open.complaint_line" in issue.field for issue in issues)
    assert any("25 words" in issue.message for issue in issues)


def test_validate_script_requires_first_interference():
    """Validation requires interference after first segment."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q", answer="a", interference_after=False),  # WRONG - should be True
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
            InterviewSegment(question="q", answer="a"),
        ]),
        signoff="Stay safe"
    )

    issues = validate_script(script)
    assert len(issues) > 0
    assert any("interview_segments[0]" in issue.field for issue in issues)
    assert any("interference" in issue.message.lower() for issue in issues)
