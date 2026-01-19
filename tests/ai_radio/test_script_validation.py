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
