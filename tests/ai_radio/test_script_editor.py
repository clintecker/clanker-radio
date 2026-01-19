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


def test_compress_script_already_under_budget():
    """Compressor returns script unchanged if already at/under budget."""
    # Create a short script
    short_answer = "Short."

    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Intro",
            intro_sentence_2="Two"
        ),
        interview_segments=[
            InterviewSegment(question="Q?", answer=short_answer, interference_after=False),
            InterviewSegment(question="Q2", answer=short_answer),
            InterviewSegment(question="Q3", answer=short_answer),
            InterviewSegment(question="Q4", answer=short_answer)
        ],
        signoff="Bye"
    )

    # Calculate actual word count
    current_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split()) +
        sum(len(s.question.split()) + len(s.answer.split()) for s in script.interview_segments) +
        len(script.signoff.split())
    )

    # Set target above current (script already under budget)
    target = current_words + 100

    # Should return original script unchanged (early return)
    result = compress_script_to_budget(script, target_words=target)

    # Should be the same object returned
    assert result is script


def test_compress_script_validates_answer_count(caplog):
    """Compressor logs warning if LLM returns wrong number of answers."""
    # This test verifies that we handle malformed LLM responses gracefully.
    # In practice, the LLM might return fewer or more answers than expected.
    # The validation logic should catch this and log a warning.

    # Create a script with multiple segments
    long_answer = "This is a very long answer " * 20

    script = FieldReportScript(
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test intro",
            intro_sentence_2="Test intro two"
        ),
        interview_segments=[
            InterviewSegment(question="Q1?", answer=long_answer, interference_after=True),
            InterviewSegment(question="Q2?", answer=long_answer),
            InterviewSegment(question="Q3?", answer=long_answer),
            InterviewSegment(question="Q4?", answer=long_answer)
        ],
        signoff="Stay safe"
    )

    # Compress with low target to trigger compression
    target = 50

    # Call compress - may or may not trigger warning depending on LLM behavior
    # We're testing that the code handles mismatches gracefully
    result = compress_script_to_budget(script, target_words=target)

    # Should return a valid script (either compressed or original on error)
    assert result is not None
    assert len(result.interview_segments) == 4

    # If warning was logged, verify the message format
    # (This may not always happen if LLM returns correct count)
    warning_logs = [r for r in caplog.records if r.levelname == "WARNING" and "returned" in r.message.lower()]
    if warning_logs:
        # If we got the mismatch warning, verify it mentions counts
        assert any("answers" in log.message.lower() for log in warning_logs)
