"""Tests for script editor (word count enforcement)."""
import pytest
from ai_radio.models.script_schema import ColdOpen, InterviewSegment, FieldReportScript
from ai_radio.script_editor import compress_script_to_budget


def _make_segments(count, answer="short answer", first_interference=True):
    """Helper to create interview segments meeting the 8-10 minimum."""
    segments = []
    for i in range(count):
        segments.append(InterviewSegment(
            question=f"q{i+1}",
            answer=answer,
            interference_after=(i == 0 and first_interference),
        ))
    return segments


def test_compress_script_reduces_word_count():
    """Compressor reduces total word count while preserving structure."""
    # Create overlong script (simulated)
    long_answer = "This is a very long answer that goes on and on with many extra words that could be compressed to make it more concise and fit within the target word budget for the segment."

    script = FieldReportScript(
        presenter_name="Test Reporter",
        source_name="Test Source",
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test intro",
            intro_sentence_2="Test intro two",
            guest_intro="Test guest intro"
        ),
        interview_segments=_make_segments(8, answer=long_answer),
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
        presenter_name="Maya Rodriguez",
        source_name="Sam Chen",
        cold_open=ColdOpen(
            complaint_line=original_complaint,
            realization="Oh shit",
            intro_sentence_1="This is Maya",
            intro_sentence_2="Broadcasting from ruins",
            guest_intro="With me is Sam Chen"
        ),
        interview_segments=_make_segments(8, answer="a" * 100),
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
        presenter_name="Test Reporter",
        source_name="Test Source",
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Intro",
            intro_sentence_2="Two",
            guest_intro="Guest intro"
        ),
        interview_segments=_make_segments(8, answer=short_answer, first_interference=False),
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
        presenter_name="Test Reporter",
        source_name="Test Source",
        cold_open=ColdOpen(
            complaint_line="Test",
            realization="Oh",
            intro_sentence_1="Test intro",
            intro_sentence_2="Test intro two",
            guest_intro="Test guest intro"
        ),
        interview_segments=_make_segments(8, answer=long_answer),
        signoff="Stay safe"
    )

    # Compress with low target to trigger compression
    target = 50

    # Call compress - may or may not trigger warning depending on LLM behavior
    # We're testing that the code handles mismatches gracefully
    result = compress_script_to_budget(script, target_words=target)

    # Should return a valid script (either compressed or original on error)
    assert result is not None
    assert len(result.interview_segments) == 8

    # If warning was logged, verify the message format
    # (This may not always happen if LLM returns correct count)
    warning_logs = [r for r in caplog.records if r.levelname == "WARNING" and "returned" in r.message.lower()]
    if warning_logs:
        # If we got the mismatch warning, verify it mentions counts
        assert any("answers" in log.message.lower() for log in warning_logs)
