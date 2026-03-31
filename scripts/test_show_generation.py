#!/usr/bin/env python3
"""Test script to generate a show and inspect TTS output."""

import sys
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.show_generator import ShowGenerator, research_topics, generate_interview_script, synthesize_show_audio
from datetime import datetime

def main():
    """Generate show 2 for testing."""
    # Connect to database
    conn = sqlite3.connect(config.paths.db_path)
    cursor = conn.cursor()

    # Get schedule details
    cursor.execute("""
        SELECT name, format, topic_area, personas, content_guidance
        FROM show_schedules WHERE id = 1
    """)
    row = cursor.fetchone()
    if not row:
        print("ERROR: Schedule 1 not found")
        return 1

    name, format_type, topic_area, personas_json, content_guidance = row

    print(f"🎬 Generating {name}")
    print(f"   Format: {format_type}")
    print(f"   Topic: {topic_area}")
    print()

    # Parse personas
    import json
    personas = json.loads(personas_json)

    # Step 1: Research topics
    print("📚 Researching topics...")
    topics = research_topics(topic_area, content_guidance or "")
    print(f"   Found {len(topics)} topics")
    for i, topic in enumerate(topics, 1):
        print(f"   {i}. {topic[:80]}...")

    # Step 2: Generate script
    print()
    print("✍️  Generating interview script...")
    script_text = generate_interview_script(
        topics=topics,
        personas=personas
    )
    print(f"   Script length: {len(script_text)} characters")
    print(f"   Word count: {len(script_text.split())} words")

    # Save script to database
    cursor.execute("""
        UPDATE generated_shows
        SET script_text = ?, status = 'script_complete', updated_at = ?
        WHERE id = 3
    """, (script_text, datetime.now().isoformat()))
    conn.commit()

    # Step 3: Synthesize audio
    print()
    print("🔊 Synthesizing audio (watch for diagnostics)...")
    from pathlib import Path
    import tempfile

    # Create temp output path
    output_path = Path(f"/srv/ai_radio/tmp/show_3_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")

    audio_file = synthesize_show_audio(
        script_text=script_text,
        personas=personas,
        output_path=output_path
    )

    print()
    print(f"✅ Audio generated: {output_path}")
    print(f"   Estimated duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Voices: {audio_file.voice}")
    print()
    print(f"Check logs above for TTS diagnostics!")

    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
