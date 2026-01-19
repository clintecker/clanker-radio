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
