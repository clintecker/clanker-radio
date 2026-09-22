#!/usr/bin/env python3
"""Test script for generating a cold open where presenter doesn't know they're on air."""

import sys
from pathlib import Path
from datetime import datetime
import logging

import google.genai as genai

from ai_radio.config import config
from ai_radio.show_generator import synthesize_show_audio
from ai_radio.world_prompt import build_world_preamble

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging to see STT/LLM processing
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

def generate_field_report_json(
    seed_theme: str = None
) -> str:
    """Generate field report as structured JSON using schema.

    Generates everything: interviewer, interviewee, locations, organizations,
    events, tactics - the whole resistance universe from scratch.

    Args:
        seed_theme: Optional theme to guide generation (e.g., "community defense",
                   "food distribution", "tech resistance"). If None, LLM chooses.

    Returns:
        JSON string matching FieldReportScript schema with embedded speaker names
    """
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    theme_guidance = f"\n\nTHEME FOCUS: {seed_theme}" if seed_theme else ""

    preamble = build_world_preamble(
        f"You write a field report for {config.station.station_name}, broadcasting from "
        f"{config.station_location}: a reporter out somewhere in this world, talking with one person "
        "they know and trust about something that matters here."
    )
    prompt = f"""{preamble}

## THIS REPORT
Invent all of it from inside this world: the reporter's name, the person they're talking to, where they are, what's going on, the people and groups involved, and what it costs them. Names, places and groups belong to this world and are specific, never generic. Things that happened have consequences: who it helped, who it hurt, what changed.{theme_guidance}

The two of them know each other, so the questions are direct and personal and build on the last answer, not on a list. Answers are concrete: named people and places, what was done, how it went. They talk loosely, with contractions, and sometimes correct themselves; nobody sounds like a press release or makes a speech.

## THE FIELDS (parsed by the renderer; keep every field and every limit)
cold_open:
- complaint_line: the reporter, not yet aware the mic is live, mutters about something going wrong where they are. Target about 15 words, max 25.
- realization: the reporter realizes they're on air. Three to five words, max 5.
- intro_sentence_1: normal voice now; the reporter gives their name and the program. Target about 20 words, max 30.
- intro_sentence_2: a routine on-air formality that belongs to how broadcasting works in this world, said in passing. Target 25 to 30 words, max 35.
- guest_intro: introduces the guest by name and what they do. Target 20 to 30 words, max 35.

interview_segments: 8 to 10 items, each with:
- question: the reporter's question. Target 35 to 40 words, max 50.
- answer: the guest's answer. Target 50 to 60 words, max 70.
- interference_after: true ONLY on segments 0, 3 and 6; false on all others.
- interference_phrase: only when interference_after is true. The reporter's short, plain reaction to the signal dropping out, 5 to 12 words, starting with one delivery cue in square brackets. Word it differently each time.

signoff: the reporter signs off plainly. Target 20 to 25 words, max 30.

Whole script: 1,000 to 1,200 words, never more than 1,400. These limits are checked; stay inside them.

## OUTPUT
Valid JSON with exactly this structure:
{{
  "presenter_name": "First Last",
  "source_name": "First Last",
  "cold_open": {{
    "complaint_line": "...",
    "realization": "...",
    "intro_sentence_1": "...",
    "intro_sentence_2": "...",
    "guest_intro": "..."
  }},
  "interview_segments": [
    {{
      "question": "...",
      "answer": "...",
      "interference_after": true,
      "interference_phrase": "[cue] ..."
    }},
    {{
      "question": "...",
      "answer": "...",
      "interference_after": false
    }},
    ...
  ],
  "signoff": "..."
}}"""

    response = client.models.generate_content(
        model=config.gemini_text_model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json"
        )
    )

    return response.text

def generate_cold_open_with_field_report(presenter_name: str, source_name: str, topics: list[str]) -> str:
    """Generate a cold open + full field report with two speakers.

    Args:
        presenter_name: Name of the field reporter
        source_name: Name of the interview source
        topics: List of topics to cover

    Returns:
        Complete script with cold open + field report
    """
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    topics_text = '\n'.join([f"- {topic}" for topic in topics])

    preamble = build_world_preamble(
        f"You write a field report for {config.station.station_name}, broadcasting from "
        f"{config.station_location}: {presenter_name} is out somewhere in this world talking with {source_name}."
    )
    prompt = f"""{preamble}

## THIS REPORT
- {presenter_name}: the field reporter.
- {source_name}: someone involved, whom {presenter_name} knows.
Topics:
{topics_text}
They talk about the work, what's going wrong, who it affects here, and what happens next. Questions are short and direct; answers are two or three plain sentences with specifics.

## STRUCTURE (the audio pipeline depends on it)
1. Cold open: one or two lines where {presenter_name}, not knowing the mic is live, mutters in [whispering] about something going wrong where they are. Then a short line realizing they're on air. Then exactly two sentences of introduction in a normal voice, no [whispering] from here on.
2. After {source_name}'s first answer, {presenter_name} says a short plain line acknowledging the signal dropped.
3. Right after {presenter_name}'s third question, a second such line, worded differently.
4. After the fifth or sixth exchange, a third, worded differently.
5. Near the end, a fourth, worded differently; then {presenter_name} wraps up and signs off plainly.
Total: 700 to 900 words.

## OUTPUT FORMAT
Every line starts with [speaker: {presenter_name}] or [speaker: {source_name}], then the words on the same line. A line may carry delivery cues in square brackets (such as [whispering], [sigh], [short pause]); use them where a performer needs them, not everywhere. Spoken words only."""

    response = client.models.generate_content(
        model=config.gemini_text_model,
        contents=prompt
    )

    return response.text

def test_json_workflow_end_to_end():
    """Test complete JSON workflow: generate → validate → repair → render."""
    import json
    from ai_radio.models.script_schema import FieldReportScript
    from ai_radio.script_validation import validate_script
    from ai_radio.script_repair import repair_script
    from ai_radio.script_renderer import render_script

    presenter = "Maya Rodriguez"
    source = "Sam Chen"
    topics = ["Test organizing work"]

    # Generate JSON
    json_output = generate_field_report_json(presenter, source, topics)
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    # Validate
    issues = validate_script(script)

    # Repair if needed
    if issues:
        script = repair_script(script)

    # Render to final format
    final_script, metadata = render_script(script, presenter, source)

    # Verify structure
    assert "[speaker: Maya Rodriguez]" in final_script
    assert "[speaker: Sam Chen]" in final_script
    assert "[whispering]" in final_script  # Cold open

    # Verify interference templates injected
    has_interference = any(
        phrase in final_script.lower()
        for phrase in ["sorry about", "jammers", "signal"]
    )
    assert has_interference

    print("✅ End-to-end JSON workflow successful")
    return final_script

def main():
    """Generate and synthesize field report using JSON schema workflow."""
    import json
    from ai_radio.models.script_schema import FieldReportScript
    from ai_radio.script_validation import validate_script
    from ai_radio.script_repair import repair_script
    from ai_radio.script_editor import compress_script_to_budget
    from ai_radio.script_renderer import render_script

    print("🎬 Generating Field Report with JSON Schema Workflow")
    print("   Letting AI invent the entire universe...")
    print()

    # Step 1: Generate structured JSON (AI invents everything)
    print("✍️  Generating structured JSON with schema...")
    json_output = generate_field_report_json()  # No hardcoded inputs!
    data = json.loads(json_output)
    script = FieldReportScript(**data)

    # Extract generated names
    presenter_name = script.presenter_name
    source_name = script.source_name

    print(f"   ✅ Valid JSON structure generated")
    print(f"   📻 Generated reporter: {presenter_name}")
    print(f"   🎤 Generated source: {source_name}")
    print()

    # Step 2: Validate structure
    print("🔍 Validating structure...")
    issues = validate_script(script)
    if issues:
        print(f"   ⚠️  Found {len(issues)} validation issues:")
        for issue in issues:
            print(f"      - {issue.field}: {issue.message}")
    else:
        print(f"   ✅ No validation issues")
    print()

    # Step 3: Repair if needed
    if issues:
        print("🔧 Repairing violations...")
        script = repair_script(script)
        print(f"   ✅ Repairs applied")
        print()

    # Step 4: Compress if over budget
    print("✂️  Checking word count budget...")
    script = compress_script_to_budget(script, target_words=1200)
    print(f"   ✅ Word count within budget")
    print()

    # Step 5: Render to final script
    print("📝 Rendering final script with programmatic interference...")
    final_script, metadata = render_script(script, presenter_name, source_name)

    word_count = len(final_script.split())
    print(f"   Script length: {len(final_script)} characters")
    print(f"   Word count: {word_count} words")
    print()

    # Display metadata about acknowledgment phrases
    print(f"📊 Metadata:")
    print(f"   Total lines: {metadata['total_lines']}")
    print(f"   Total words: {metadata['total_words']}")
    print(f"   Acknowledgment phrases: {len(metadata['acknowledgment_phrases'])}")
    for ack in metadata["acknowledgment_phrases"]:
        print(f"      - Line {ack['line_num']}: {ack['phrase'][:60]}...")
    print()

    print("=" * 60)
    print(final_script)
    print("=" * 60)
    print()

    # Step 6: Synthesize with two speakers and background bed
    print("🔊 Synthesizing audio with background bed...")
    output_path = Path(f"/tmp/field-report-json-{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")

    personas = [
        {"name": presenter_name, "traits": "female field reporter"},
        {"name": source_name, "traits": "male organizer from resistance"}
    ]

    audio_file = synthesize_show_audio(
        script_text=final_script,
        personas=personas,
        output_path=output_path,
        add_bed=True,  # Add background bed with ducking
        interference_metadata=metadata  # Pass metadata for synchronized interference timing
    )

    print()
    print(f"✅ Field report generated: {output_path}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Voices: {audio_file.voice}")
    print()
    print("🎯 JSON Schema Workflow Benefits:")
    print("  ✓ Reliable cold open timing (enforced by schema)")
    print("  ✓ Programmatic interference injection (templates)")
    print("  ✓ Word budget constraints (validated + compressed)")
    print("  ✓ Structural guarantees (Pydantic models)")
    print("  ✓ LLM-assisted compression (defense-in-depth)")
    print()
    print("📊 Metrics:")
    print(f"  - Total words: {word_count}")
    print(f"  - Cold open: ~{len(script.cold_open.complaint_line.split()) + len(script.cold_open.intro_sentence_1.split()) + len(script.cold_open.intro_sentence_2.split()) + len(script.cold_open.guest_intro.split())} words")
    print(f"  - Interview segments: {len(script.interview_segments)}")
    print(f"  - Duration estimate: {audio_file.duration_estimate:.1f}s (~{audio_file.duration_estimate/60:.1f} min)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
