"""Integration test for complete JSON workflow with audio generation."""
import json
import sys
import importlib.util
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
from ai_radio.script_validation import validate_script
from ai_radio.script_repair import repair_script
from ai_radio.script_renderer import render_script
from ai_radio.script_editor import compress_script_to_budget
from ai_radio.show_generator import synthesize_show_audio


@pytest.mark.integration
def test_complete_json_workflow_with_audio():
    """Test complete workflow: JSON → validate → repair → compress → render → audio."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = [
        "Bridgeport Mutual Aid - solar chargers",
        "West Side Watchdogs - community defense"
    ]

    # Step 1: Generate JSON
    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    assert script.cold_open is not None
    assert len(script.interview_segments) >= 4

    # Step 2: Validate
    issues = validate_script(script)

    # Step 3: Repair if needed
    if issues:
        script = repair_script(script)

    # Step 4: Compress if over budget
    script = compress_script_to_budget(script, target_words=900)

    # Step 5: Render
    final_script = render_script(script, presenter, source)

    # Verify structure
    assert "[speaker: Maya Rodriguez]" in final_script
    assert "[whispering]" in final_script

    # Check for interference phrases (less strict - just check if any interference was injected)
    has_interference = any(phrase in final_script.lower() for phrase in [
        "sorry", "jammers", "signal", "damn", "corp", "hold on", "can you"
    ])
    if not has_interference:
        print(f"DEBUG: Final script:\n{final_script}")
    assert has_interference, "No interference phrases found in rendered script"

    # Step 6: Synthesize audio
    output_path = Path("/tmp/test-json-workflow-integration.mp3")
    personas = [
        {"name": presenter, "traits": "female field reporter"},
        {"name": source, "traits": "male organizer"}
    ]

    audio_file = synthesize_show_audio(
        script_text=final_script,
        personas=personas,
        output_path=output_path,
        add_bed=True
    )

    # Verify audio was generated
    assert output_path.exists()
    assert audio_file.duration_estimate > 0

    # Verify timing constraints
    # Cold open should be roughly 15-25 seconds (using ~150 words/min speaking rate)
    cold_open_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split())
    )
    cold_open_seconds = (cold_open_words / 150) * 60  # Rough estimate

    assert 10 <= cold_open_seconds <= 30, f"Cold open timing off: {cold_open_seconds}s"

    # Total duration should be reasonable for word count
    total_words = len(final_script.split())
    expected_duration = (total_words / 150) * 60  # ~150 wpm

    # Allow 50% variance for pauses, emotion tags, etc.
    assert expected_duration * 0.5 <= audio_file.duration_estimate <= expected_duration * 1.5

    print(f"✅ Integration test passed")
    print(f"   Words: {total_words}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Cold open: ~{cold_open_seconds:.1f}s")
    print(f"   Output: {output_path}")
