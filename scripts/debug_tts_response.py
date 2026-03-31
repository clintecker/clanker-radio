#!/usr/bin/env python3
"""Diagnostic script to inspect Gemini TTS API response structure."""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
import google.genai as genai
import google.genai.types

def main():
    """Fetch show script and call TTS to inspect response structure."""
    # Get script directly from database
    conn = sqlite3.connect(config.paths.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT script_text FROM generated_shows WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        print("ERROR: Show 1 has no script")
        return 1

    script_text = row[0]
    print(f"Script length: {len(script_text)} characters")
    print(f"Word count: {len(script_text.split())} words")
    print()

    # Call Gemini TTS
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    print("Calling Gemini TTS API...")
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=script_text,
        config=google.genai.types.GenerateContentConfig(
            response_modalities=["AUDIO"]
        )
    )

    print("\n=== RESPONSE STRUCTURE ===")
    print(f"Number of candidates: {len(response.candidates)}")

    for i, candidate in enumerate(response.candidates):
        print(f"\nCandidate {i}:")
        print(f"  Number of parts: {len(candidate.content.parts)}")

        for j, part in enumerate(candidate.content.parts):
            if hasattr(part, 'inline_data') and part.inline_data:
                audio_size = len(part.inline_data.data) if part.inline_data.data else 0
                # PCM 24kHz 16-bit mono = 48000 bytes per second
                duration_estimate = audio_size / 48000
                print(f"  Part {j}:")
                print(f"    Audio data size: {audio_size:,} bytes")
                print(f"    Estimated duration: {duration_estimate:.1f} seconds")
            else:
                print(f"  Part {j}: No inline_data")

    return 0

if __name__ == "__main__":
    sys.exit(main())
