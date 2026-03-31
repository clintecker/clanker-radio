#!/usr/bin/env python3
"""Debug script to trace interference detection data flow."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.show_generator import extract_word_timestamps_with_whisper, identify_interference_points_with_llm

def main():
    # Use the most recent test file
    audio_file = Path("/tmp/field-report-cold-open-20260119_011113.mp3")

    if not audio_file.exists():
        print(f"ERROR: Audio file not found: {audio_file}")
        return 1

    print("=" * 80)
    print("DEBUGGING INTERFERENCE DETECTION")
    print("=" * 80)
    print()

    # Step 1: Extract word timestamps with Whisper
    print("STEP 1: Running Whisper STT...")
    print("-" * 80)
    word_timestamps = extract_word_timestamps_with_whisper(audio_file)

    print(f"\nWhisper extracted {len(word_timestamps)} words")
    print()
    print("First 50 words:")
    for i, word in enumerate(word_timestamps[:50]):
        print(f"{word['start']:6.2f}s: {word['word']}")

    print()
    print("Last 50 words:")
    for i, word in enumerate(word_timestamps[-50:]):
        print(f"{word['start']:6.2f}s: {word['word']}")

    print()
    print("=" * 80)

    # Step 2: Create a sample script with known acknowledgment phrases
    sample_script = """
[speaker: Maya Rodriguez] [whispering] This is a test broadcast.
[speaker: Maya Rodriguez] [shocked] Oh shit. Oh.
[speaker: Maya Rodriguez] Sorry about that, someone's trying to jam us again...
[speaker: Maya Rodriguez] Can you still hear me? Signal's spotty today...
[speaker: Maya Rodriguez] Damn corp jammers... where was I?
[speaker: Maya Rodriguez] Let me adjust the antenna... there, that's better.
[speaker: Maya Rodriguez] Hold on... okay, signal's back.
"""

    print("STEP 2: Running LLM Analysis...")
    print("-" * 80)
    print(f"Sample script has {len(sample_script)} characters")
    print()

    # Show what the LLM will receive (formatted transcript)
    print("Formatted transcript (first 100 lines):")
    formatted_lines = []
    for word_data in word_timestamps[:100]:
        formatted_lines.append(f"{word_data['start']:.2f}s: {word_data['word']}")

    for line in formatted_lines:
        print(line)

    print()
    print("=" * 80)

    # Step 3: Run LLM analysis
    interference_points = identify_interference_points_with_llm(word_timestamps, sample_script)

    print()
    print("STEP 3: LLM Results")
    print("-" * 80)
    print(f"Identified {len(interference_points)} interference points:")
    for i, timestamp in enumerate(interference_points, 1):
        print(f"  {i}. {timestamp:.2f}s")

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
