#!/usr/bin/env python3
"""Test different Gemini TTS voices for comparison.

Generates test breaks with multiple voice options so you can compare them.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Voice options to test (various voice characteristics for DJ comparison)
VOICES_TO_TEST = [
    ("Kore", "Firm - Authoritative, solid"),
    ("Enceladus", "Breathy - Tired, weary sound"),
    ("Aoede", "Breezy - Casual, laid-back"),
    ("Umbriel", "Easy-going - Relaxed survivor"),
    ("Puck", "Upbeat - Current default"),
    ("Orus", "Firm - Another authoritative option"),
]

print("Generating test breaks with different Gemini voices...")
print("This will create 6 test breaks - one for each voice.\n")

for voice_name, description in VOICES_TO_TEST:
    print(f"Generating with {voice_name} ({description})...")

    # Set environment variable and generate break
    import os
    os.environ["RADIO_TTS_PROVIDER"] = "gemini"
    os.environ["RADIO_GEMINI_TTS_VOICE"] = voice_name

    # Import after setting env vars
    from ai_radio.break_generator import generate_break

    result = generate_break()

    if result:
        # Rename file to include voice name
        new_name = result.file_path.parent / f"test_{voice_name.lower()}.mp3"
        result.file_path.rename(new_name)
        print(f"  ✓ Saved: {new_name.name} ({result.duration:.1f}s)\n")
    else:
        print(f"  ✗ Failed to generate with {voice_name}\n")

print(f"Done! Check {config.breaks_path}/ for test_*.mp3 files")
