#!/usr/bin/env python3
"""Test script to generate a field report show with background bed."""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.show_generator import research_topics, generate_field_report_script, synthesize_show_audio

def main():
    """Generate field report show for testing."""

    # Field report personas - reporter + sources
    personas = [
        {
            "name": "Maya Rodriguez",
            "traits": "female field reporter, embedded with resistance groups"
        },
        {
            "name": "Sam Chen",
            "traits": "male organizer from the Bridgeport Mutual Aid Collective"
        }
    ]

    topic_area = "Resistance movements and civic groups organizing in the Chicago wasteland"
    content_guidance = "Focus on grassroots organizing, mutual aid networks, and community defense against corporate control"

    print("🎬 Generating Field Report")
    print(f"   Reporter: {personas[0]['name']}")
    print(f"   Source: {personas[1]['name']}")
    print()

    # Step 1: Research topics
    print("📚 Researching resistance movements...")
    topics = research_topics(topic_area, content_guidance)
    print(f"   Found {len(topics)} groups/movements:")
    for i, topic in enumerate(topics, 1):
        print(f"   {i}. {topic[:80]}...")

    # Step 2: Generate field report script
    print()
    print("✍️  Generating field report script...")
    script_text = generate_field_report_script(
        topics=topics,
        personas=personas
    )
    print(f"   Script length: {len(script_text)} characters")
    print(f"   Word count: {len(script_text.split())} words")

    # Step 3: Synthesize audio WITH background bed
    print()
    print("🔊 Synthesizing audio with background bed...")
    output_path = Path(f"/tmp/field-report-test-{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")

    audio_file = synthesize_show_audio(
        script_text=script_text,
        personas=personas,
        output_path=output_path,
        add_bed=True  # This will add background music with ducking
    )

    print()
    print(f"✅ Field report generated: {output_path}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Voices: {audio_file.voice}")
    print()
    print("Listen to verify:")
    print(f"  - Background music loops throughout")
    print(f"  - Music ducks to 15% during voice")
    print(f"  - Full volume for 3sec intro/outro")

    return 0

if __name__ == "__main__":
    sys.exit(main())
