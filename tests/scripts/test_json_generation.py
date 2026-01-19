"""Tests for JSON schema based script generation."""
import json
import sys
import importlib.util
from pathlib import Path

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


def test_generate_field_report_json_returns_valid_structure():
    """JSON generation returns valid FieldReportScript."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = [
        "Bridgeport Mutual Aid - solar chargers",
        "West Side Watchdogs - community defense"
    ]

    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)

    # Should parse as valid FieldReportScript
    script = FieldReportScript(**data)

    assert script.cold_open is not None
    assert len(script.interview_segments) >= 4
    assert len(script.interview_segments) <= 6
    assert script.signoff is not None


def test_first_segment_has_interference():
    """First interview segment should have interference_after=True."""
    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = ["Test topic"]

    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    assert script.interview_segments[0].interference_after is True
