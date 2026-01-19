"""Tests for script schema data models."""
import pytest
from pydantic import ValidationError
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
    with pytest.raises(ValidationError):
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
