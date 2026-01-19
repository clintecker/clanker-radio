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
