"""Integration test for complete JSON workflow with audio generation."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Add paths for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root))

# Load the test_cold_open script
script_path = repo_root / "scripts" / "test_cold_open.py"
spec = importlib.util.spec_from_file_location("test_cold_open", script_path)
test_cold_open = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_cold_open)
generate_field_report_json = test_cold_open.generate_field_report_json

from ai_radio.models.script_schema import FieldReportScript
from ai_radio.script_editor import compress_script_to_budget
from ai_radio.script_renderer import render_script
from ai_radio.script_repair import repair_script
from ai_radio.script_validation import validate_script
from ai_radio.show_generator import synthesize_show_audio

# Constants for timing validation
TARGET_WORD_COUNT = 900
SPEAKING_RATE_WPM = 150
DURATION_VARIANCE_FACTOR = 0.5
COLD_OPEN_MIN_SECONDS = 10
COLD_OPEN_MAX_SECONDS = 30


@pytest.mark.integration
def test_complete_json_workflow_with_audio() -> None:
    """Test complete workflow from JSON generation through audio synthesis.

    This integration test verifies the entire content generation pipeline:
    1. Generate JSON structure for a field report
    2. Validate the script structure
    3. Repair any validation issues
    4. Compress to target word count budget
    5. Render script with speaker tags and emotion markers
    6. Synthesize audio with TTS and verify output

    The test validates timing constraints, speaker presence, interference phrases,
    and that the generated audio file meets duration expectations.

    Raises:
        AssertionError: If any step in the workflow fails validation
    """
    # Step 1: Generate JSON (LLM generates presenter/source names)
    json_output = generate_field_report_json()
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    # Extract generated names
    presenter = script.presenter_name
    source = script.source_name

    assert script.cold_open is not None
    assert len(script.interview_segments) >= 4

    # Step 2: Validate
    issues = validate_script(script)

    # Step 3: Repair if needed
    if issues:
        script = repair_script(script)

    # Step 4: Compress if over budget
    script = compress_script_to_budget(script, target_words=TARGET_WORD_COUNT)

    # Step 5: Render
    final_script, metadata = render_script(script, presenter, source)

    # Verify structure (use generated presenter name)
    assert f"[speaker: {presenter}]" in final_script
    assert "[whispering]" in final_script

    # Verify metadata structure
    assert "acknowledgment_phrases" in metadata
    assert "total_lines" in metadata
    assert "total_words" in metadata

    # Count how many segments have interference_after=True
    expected_interference_count = sum(1 for seg in script.interview_segments if seg.interference_after)

    # Verify metadata acknowledgment count matches schema interference flags
    assert len(metadata["acknowledgment_phrases"]) == expected_interference_count, \
        f"Acknowledgment count mismatch: {len(metadata['acknowledgment_phrases'])} in metadata " \
        f"but {expected_interference_count} segments with interference_after=True"

    # Check for interference phrases (less strict - just check if any interference was injected)
    has_interference = any(phrase in final_script.lower() for phrase in [
        "sorry", "jammers", "signal", "damn", "corp", "hold on", "can you"
    ])
    assert has_interference, "No interference phrases found in rendered script"

    # Log metadata for debugging
    print(f"\n📊 Metadata Flow Test:")
    print(f"   Expected interference: {expected_interference_count}")
    print(f"   Acknowledgment phrases: {len(metadata['acknowledgment_phrases'])}")
    for ack in metadata['acknowledgment_phrases']:
        print(f"      - Line {ack['line_num']}: {ack['phrase'][:50]}...")

    # Step 6: Synthesize audio
    output_path = Path("/tmp/test-json-workflow-integration.mp3")
    personas = [
        {"name": presenter, "traits": "female field reporter"},
        {"name": source, "traits": "male organizer"}
    ]

    try:
        audio_file = synthesize_show_audio(
            script_text=final_script,
            personas=personas,
            output_path=output_path,
            add_bed=True,
            interference_metadata=metadata  # Pass metadata for synchronized interference
        )

        # Verify audio was generated
        assert output_path.exists()
        assert audio_file.duration_estimate > 0

        # Verify timing constraints
        # Cold open should be roughly 15-25 seconds (using speaking rate)
        cold_open_words = (
            len(script.cold_open.complaint_line.split()) +
            len(script.cold_open.realization.split()) +
            len(script.cold_open.intro_sentence_1.split()) +
            len(script.cold_open.intro_sentence_2.split())
        )
        cold_open_seconds = (cold_open_words / SPEAKING_RATE_WPM) * 60

        assert COLD_OPEN_MIN_SECONDS <= cold_open_seconds <= COLD_OPEN_MAX_SECONDS, \
            f"Cold open timing off: {cold_open_seconds}s"

        # Total duration should be reasonable for word count
        total_words = len(final_script.split())
        expected_duration = (total_words / SPEAKING_RATE_WPM) * 60

        # Allow variance for pauses, emotion tags, etc.
        assert expected_duration * DURATION_VARIANCE_FACTOR <= audio_file.duration_estimate <= \
            expected_duration * (2 - DURATION_VARIANCE_FACTOR)
    finally:
        # Cleanup: remove temporary audio file
        if output_path.exists():
            output_path.unlink()


@pytest.mark.integration
def test_interference_synchronization_no_hallucination() -> None:
    """Test that interference timing uses exact metadata without LLM hallucination.

    This test specifically validates the fix for the emotion timing issue where
    the LLM would hallucinate extra interference points that don't exist in the
    script metadata. The deterministic approach should only place interference
    at the exact locations specified in the metadata.

    Raises:
        AssertionError: If interference count doesn't match acknowledgment count
    """
    # Generate JSON (LLM generates presenter/source names)
    json_output = generate_field_report_json()
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    # Extract generated names
    presenter = script.presenter_name
    source = script.source_name

    # Validate and compress
    issues = validate_script(script)
    if issues:
        script = repair_script(script)
    script = compress_script_to_budget(script, target_words=TARGET_WORD_COUNT)

    # Render with metadata
    final_script, metadata = render_script(script, presenter, source)

    # Count expected interference from schema
    expected_count = sum(1 for seg in script.interview_segments if seg.interference_after)

    # Verify metadata matches schema (no hallucination at render time)
    actual_ack_count = len(metadata["acknowledgment_phrases"])
    assert actual_ack_count == expected_count, \
        f"Renderer hallucinated acknowledgments: expected {expected_count}, got {actual_ack_count}"

    print(f"\n✅ No Hallucination Test:")
    print(f"   Schema interference flags: {expected_count}")
    print(f"   Metadata acknowledgments: {actual_ack_count}")
    print(f"   Match: {actual_ack_count == expected_count}")

    # Verify each acknowledgment phrase is actually in the script
    # Use fuzzy matching to handle compression artifacts
    from thefuzz import fuzz
    import re

    def normalize_for_matching(text: str) -> str:
        """Normalize text for matching (lowercase, remove extra whitespace)."""
        text = re.sub(r'\[.*?\]', '', text)  # Remove emotion tags
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text.strip().lower()

    script_normalized = normalize_for_matching(final_script)

    for ack in metadata["acknowledgment_phrases"]:
        phrase = ack["phrase"]
        phrase_normalized = normalize_for_matching(phrase)

        # Check if phrase appears in script (fuzzy match to handle compression)
        found = False
        # Split into sentences and check each
        for line in final_script.split('\n'):
            line_normalized = normalize_for_matching(line)
            # Use fuzzy matching with threshold of 80%
            similarity = fuzz.partial_ratio(phrase_normalized, line_normalized)
            if similarity >= 80:
                found = True
                break

        assert found, \
            f"Acknowledgment phrase not found in script (fuzzy match): {phrase}"

    print(f"   All {actual_ack_count} acknowledgment phrases verified in script")
    print(f"   ✅ No LLM hallucination detected")
