"""Tests for script repair logic."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_repair import repair_script
from ai_radio.script_validation import validate_script


def _cold_open():
    return ColdOpen(
        complaint_line="Test",
        realization="Oh",
        intro_sentence_1="Test",
        intro_sentence_2="Test",
        guest_intro="Test guest intro",
    )


def _pad_segments(segments, target=8):
    """Pad segment list to target count."""
    while len(segments) < target:
        segments.append(InterviewSegment(
            question=f"q_pad{len(segments)+1}",
            answer=f"a_pad{len(segments)+1}",
            interference_after=False,
        ))
    return segments


def test_repair_script_fixes_missing_first_interference():
    """Repair ensures first segment has interference_after=True."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q1", answer="a1", interference_after=False),  # WRONG
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False),
        ]),
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
    """Repair adds second interference on fourth segment (index 3) if 7+ segments."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q1", answer="a1", interference_after=True),
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False),
            InterviewSegment(question="q5", answer="a5", interference_after=False),
        ]),
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Should ensure segment 3 has interference (7+ segment threshold)
    assert repaired.interview_segments[3].interference_after is True


def test_repair_script_preserves_content():
    """Repair does not modify question/answer content."""
    original_question = "What organizing work are you doing in the community?"
    original_answer = "We are building solidarity networks across neighborhoods."

    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(
                question=original_question,
                answer=original_answer,
                interference_after=False
            ),
            InterviewSegment(question="q2", answer="a2"),
            InterviewSegment(question="q3", answer="a3"),
            InterviewSegment(question="q4", answer="a4"),
        ]),
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Content should be unchanged
    assert repaired.interview_segments[0].question == original_question
    assert repaired.interview_segments[0].answer == original_answer


def test_repair_script_handles_minimum_segments():
    """Repair handles minimum segment count (8) without second interference."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q1", answer="a1", interference_after=False),
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False),
        ]),
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Should fix first segment
    assert repaired.interview_segments[0].interference_after is True
    # Count should remain the same
    assert len(repaired.interview_segments) == 8


def test_repair_script_handles_maximum_segments():
    """Repair handles maximum segment count (10) with all three interferences."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q1", answer="a1", interference_after=False),
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=False),
            InterviewSegment(question="q5", answer="a5", interference_after=False),
            InterviewSegment(question="q6", answer="a6", interference_after=False),
        ], target=10),
        signoff="Stay safe"
    )

    repaired = repair_script(script)

    # Should fix first segment
    assert repaired.interview_segments[0].interference_after is True
    # Should add second interference at index 3 (7+ segments)
    assert repaired.interview_segments[3].interference_after is True
    # Should add third interference at index 6 (8+ segments)
    assert repaired.interview_segments[6].interference_after is True
    # Count should remain the same
    assert len(repaired.interview_segments) == 10


def test_repair_script_is_idempotent():
    """Repair is safe when script already conforms to rules."""
    script = FieldReportScript(
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=_cold_open(),
        interview_segments=_pad_segments([
            InterviewSegment(question="q1", answer="a1", interference_after=True),
            InterviewSegment(question="q2", answer="a2", interference_after=False),
            InterviewSegment(question="q3", answer="a3", interference_after=False),
            InterviewSegment(question="q4", answer="a4", interference_after=True),
            InterviewSegment(question="q5", answer="a5", interference_after=False),
        ]),
        signoff="Stay safe"
    )

    # Apply repair twice
    repaired_once = repair_script(script)
    repaired_twice = repair_script(repaired_once)

    # Should be identical (idempotent) - interference at 0, 3, 6
    assert repaired_once.interview_segments[0].interference_after is True
    assert repaired_once.interview_segments[3].interference_after is True
    assert repaired_once.interview_segments[6].interference_after is True
    assert repaired_twice.interview_segments[0].interference_after is True
    assert repaired_twice.interview_segments[3].interference_after is True
    assert repaired_twice.interview_segments[6].interference_after is True
