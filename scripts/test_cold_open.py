#!/usr/bin/env python3
"""Test script for generating a cold open where presenter doesn't know they're on air."""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging to see STT/LLM processing
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

from ai_radio.config import config
from ai_radio.show_generator import synthesize_show_audio, research_topics
import google.genai as genai
import google.genai.types

def generate_field_report_json(
    presenter_name: str,
    source_name: str,
    topics: list
) -> str:
    """Generate field report as structured JSON using schema.

    Args:
        presenter_name: Name of the field reporter
        source_name: Name of the interview source
        topics: List of resistance group topics to cover

    Returns:
        JSON string matching FieldReportScript schema
    """
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    topics_text = '\n'.join([f"- {topic}" for topic in topics])

    prompt = f"""Generate a pirate radio field report as structured JSON.

WORLD CONTEXT:
{config.world.world_setting}

SPEAKERS:
- {presenter_name} (field reporter for resistance radio)
- {source_name} (organizer from resistance movement)

TOPICS:
{topics_text}

STRUCTURE REQUIREMENTS:

**cold_open** (4 fields):
- complaint_line: {presenter_name} whispers complaint about equipment/patrol (~15 words)
- realization: Shocked reaction to mic being live (e.g., "Oh shit. Oh.")
- intro_sentence_1: First introduction in normal voice (~20 words)
- intro_sentence_2: Second introduction continuing setup (~20 words)

**interview_segments** (4-6 items, each with 3 fields):
- question: {presenter_name} asks about organizing work (~25-30 words)
- answer: {source_name} responds about their work (~40-50 words)
- interference_after: Boolean - true for segments 0 and 2 (first and third Q&A)

**signoff**: {presenter_name} signs off (~15-20 words)

WORD BUDGETS (strict):
- Total cold_open: ~70 words
- Each interview segment: ~70-80 words
- Total script: 700-900 words (4-6 segments × 75 words average = 300-450 words + cold open + signoff)

CRITICAL: Set interference_after=true ONLY on segments 0 and 2. This places interference IMMEDIATELY after first answer and third answer.

OUTPUT: Valid JSON matching this exact structure:
{{{{
  "cold_open": {{{{
    "complaint_line": "...",
    "realization": "...",
    "intro_sentence_1": "...",
    "intro_sentence_2": "..."
  }}}},
  "interview_segments": [
    {{{{
      "question": "...",
      "answer": "...",
      "interference_after": true
    }}}},
    ...
  ],
  "signoff": "..."
}}}}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json"
        )
    )

    return response.text

def generate_cold_open_with_field_report(presenter_name: str, source_name: str, topics: list) -> str:
    """Generate a cold open + full field report with two speakers.

    Args:
        presenter_name: Name of the field reporter
        source_name: Name of the interview source
        topics: List of resistance group topics to cover

    Returns:
        Complete script with cold open + field report
    """
    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    topics_text = '\n'.join([f"- {topic}" for topic in topics])

    prompt = f"""Generate a complete field report with cold open for a pirate radio show.

WORLD CONTEXT:
{config.world.world_setting}
{config.world.world_tone}

SPEAKERS:
- {presenter_name} (field reporter for resistance radio)
- {source_name} (organizer from resistance movement)

<INTERVIEW_CONTEXT>
Topics for {source_name} from: {topics_text}
Interview should cover: organizing work, challenges, community impact, calls to action
Tone: Raw, immediate, grassroots energy
</INTERVIEW_CONTEXT>

CRITICAL VOICE DIRECTION:
- {presenter_name} should whisper VERY QUIETLY during cold open, as if trying not to be heard
- Use [whispering] tag for quiet delivery during cold open
- After embarrassment/realization, remove whispering tag and speak normally
- Do NOT continue whispering after the cold open!
- The contrast between whispered and normal should be DRAMATIC

EMOTION TAGS - Gemini 2.5 Pro supports 64+ emotions from Fish-Speech:
Basic: [happy] [sad] [angry] [excited] [calm] [nervous] [confident] [surprised] [satisfied] [worried] [upset] [frustrated] [embarrassed] [proud] [grateful] [curious]
Advanced: [anxious] [confused] [disappointed] [regretful] [guilty] [hopeful] [optimistic] [determined] [resigned] [contemptuous] [sympathetic] [compassionate]
Tone: [whispering] [shouting] [soft tone]
Sounds: [sigh] [laughing] [chuckling] [uhm] [gasping]
Pauses: [short pause] [medium pause] [long pause]

USE RICH EMOTIONS throughout to make the dialogue come alive! Be expressive!

OUTPUT FORMAT - Use speaker markers with expressive emotion tags:
[speaker: {presenter_name}] [whispering] [annoyed] Sam, I swear if that generator fails one more time...
[speaker: {presenter_name}] [whispering] [frustrated] ...and then the patrol almost caught us...
[speaker: {presenter_name}] [shocked] Oh shit. Oh. [medium pause]
[speaker: {presenter_name}] [embarrassed] [sigh] Right. Okay. So.
[speaker: {presenter_name}] [nervous] This is... {presenter_name}... with Field Reports...
[speaker: {presenter_name}] [confident] Broadcasting from the ruins...
[speaker: {presenter_name}] [determined] Today I'm out in Sector...
[speaker: {source_name}] [earnest] Yeah, so what we're doing is...

Make it feel REAL - technical difficulties, genuine embarrassment, then actual field reporting.

<MANDATORY_SCRIPT_STRUCTURE>

Follow these steps IN ORDER to construct the script. This is a MANDATORY SEQUENCE.

**STEP 1: GENERATE THE COLD OPEN**
- Write EXACTLY 1-2 lines where {presenter_name} complains about equipment/patrol in [whispering]
- Follow IMMEDIATELY with: {presenter_name} realizes mic is live: "[shocked] Oh shit."
- End cold open with EXACTLY 2 sentences of show introduction in NORMAL SPEAKING VOICE
- DO NOT add any other content to the cold open
- Cold open MUST end after these 2 introduction sentences

**STEP 2: BEGIN INTERVIEW AND INSERT FIRST INTERFERENCE**
- {presenter_name} asks the first interview question about {source_name}'s organizing work
- {source_name} gives a 2-3 sentence answer
- IMMEDIATELY after {source_name}'s first answer, {presenter_name} acknowledges signal interference
- Use one of: "Sorry about that, someone's trying to jam us again" / "Can you still hear me? Signal's spotty" / "Hold on... [short pause] okay, signal's back"

**STEP 3: CONTINUE INTERVIEW WITH INTERFERENCE AT QUESTION 3**
- {presenter_name} asks second question
- {source_name} answers (2-3 sentences)
- {presenter_name} asks third question
- IMMEDIATELY after third question, insert SECOND interference acknowledgment before {source_name} can answer
- Use different phrase: "Damn corp jammers... where was I?" / "Let me adjust the antenna... there, that's better"

**STEP 4: MID-INTERVIEW INTERFERENCE**
- Continue interview with 3-4 more question/answer exchanges
- After the 5th or 6th exchange, insert THIRD interference acknowledgment
- Use different phrase from previous ones

**STEP 5: LATE INTERVIEW INTERFERENCE**
- Continue interview with 2-3 more exchanges
- Insert FOURTH interference acknowledgment near the end
- {presenter_name} wraps up the interview and signs off

**STEP 6: VERIFY WORD COUNT**
- Total script should be approximately 700-900 words
- If over 1000 words, you have made the interview exchanges too long

</MANDATORY_SCRIPT_STRUCTURE>"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt
    )

    return response.text

def main():
    """Generate and synthesize field report with cold open."""
    presenter_name = "Maya Rodriguez"
    source_name = "Sam Chen"

    # Sample resistance topics
    topics = [
        "The Bridgeport Mutual Aid Collective - distributing solar chargers and water filters",
        "West Side Watchdogs - community defense patrols against corporate security",
        "Pilsen Solidarity Network - setting up mesh networks for free communication"
    ]

    print("🎬 Generating Field Report with Cold Open")
    print(f"   Presenter: {presenter_name}")
    print(f"   Source: {source_name}")
    print()

    # Generate full script with cold open
    print("✍️  Generating cold open + field report script...")
    script = generate_cold_open_with_field_report(presenter_name, source_name, topics)

    print(f"   Script length: {len(script)} characters")
    print(f"   Word count: {len(script.split())} words")
    print()
    print("=" * 60)
    print(script)
    print("=" * 60)
    print()

    # Synthesize with two speakers and background bed
    print("🔊 Synthesizing audio with background bed...")
    output_path = Path(f"/tmp/field-report-cold-open-{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")

    personas = [
        {"name": presenter_name, "traits": "female field reporter"},
        {"name": source_name, "traits": "male organizer from resistance"}
    ]

    audio_file = synthesize_show_audio(
        script_text=script,
        personas=personas,
        output_path=output_path,
        add_bed=True  # Add background bed with ducking
    )

    print()
    print(f"✅ Field report with cold open generated: {output_path}")
    print(f"   Duration: {audio_file.duration_estimate:.1f}s")
    print(f"   Voices: {audio_file.voice}")
    print()
    print("Listen to verify:")
    print("  - Whispered tones at start")
    print("  - Transition to NORMAL VOICE after embarrassment")
    print("  - Two distinct voices (Maya + Sam)")
    print("  - Background bed loops throughout")
    print("  - Music ducks during speech")

    return 0

if __name__ == "__main__":
    sys.exit(main())
