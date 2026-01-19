#!/usr/bin/env python3
"""Test script for generating a cold open where presenter doesn't know they're on air."""

import sys
from pathlib import Path
from datetime import datetime
import logging

import google.genai as genai

from ai_radio.config import config
from ai_radio.show_generator import synthesize_show_audio

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

    prompt = f"""Generate a pirate radio field report as structured JSON.

YOU MUST INVENT EVERYTHING - this is world-building:
- Create the field reporter's name (first + last, diverse backgrounds)
- Create the interviewee's name (first + last, diverse backgrounds)
- Invent 2-3 resistance organizations with specific names (NOT generic like "Resistance Group")
- Create specific Chicago neighborhood locations (West Side, Pilsen, Bridgeport, etc.)
- Invent recent events (raids, victories, losses) with named people and places
- Create specific tactics and resources (mesh networks, solar chargers, patrol routes)
- Generate consequences (injuries, arrests, victories) with real stakes{theme_guidance}

WORLD CONTEXT:
{config.world.world_setting}

TONE & ENERGY:
{config.world.world_tone}

This is ILLEGAL underground radio - urgent, raw, passionate. Not a polite interview.
- Field reporter is broadcasting under threat from a specific location in Chicago
- Interviewee is a fellow resistance fighter sharing front-line intel
- They KNOW each other, trust each other - this is comrades talking, not journalist/subject
- Questions are DIRECT and PERSONAL - "How are YOU dealing with..." not "Can you tell our listeners..."
- Answers are CONCRETE and SPECIFIC - named people, exact locations, specific tactics
- Both are ANGRY at corps, HOPEFUL about resistance, SCARED but DETERMINED

MAKE IT REAL AND BELIEVABLE - NPR-Style Natural Conversation:

ACTIVE LISTENING (Reporter must do this):
- Affirm constantly: "Yeah", "Mm-hmm", "Right", "Absolutely", "Damn"
- Reflect back: "So what you're saying is...", "Wait, you mean..."
- Validate emotion: "That must've been rough", "I can't imagine", "Shit, I'm sorry"
- Bridge topics: "Yeah. Okay, that brings me to...", "Right. So..."
- Add context they know: "I heard about that raid, but I didn't know you were there"

LAYERED QUESTIONING (Build organically):
- Start broad: "What's the situation?" → narrow from their answer
- Follow what they JUST said: "You mentioned Maria - what happened?"
- Probe: "Why that route?", "What were you thinking?"
- Clarify: "Wait, who was there?", "I'm confused, explain that again?"
- Connect: "Is that related to what you said about Bridgeport?"
- Process aloud: "I'm wondering if...", "That makes me think..."

PACING VARIATION (Not every moment same weight):
- HEAVY moments (deaths, losses): Slow down, let silence breathe, show emotion
- LIGHT moments (small wins, humor): Quick back-and-forth, both can laugh
- MEDIUM moments (tactics, planning): Practical, focused
- Pattern: Heavy → Light → Medium → Heavy (vary the rhythm)

CONVERSATIONAL REPAIRS (Real people clarify):
- "I mean...", "Wait, no, let me say that better..."
- "You know what I'm trying to say?", "Does that make sense?"
- "Actually, that's not quite right. What really happened was..."
- "How do I explain this... okay, so..."

THINKING TOGETHER (Not just Q&A):
- Reporter processes: "That makes sense because...", "I hadn't thought about it that way"
- Share observations: "What strikes me is...", "The thing that worries me..."
- Mutual problem-solving: "But wait, how does that work? That seems like it would..."
- Don't just ask - participate in the conversation

HUMOR & LIGHTNESS (Even in dark times):
- Gallows humor: "Getting shot at really makes you run faster, huh?"
- Absurdity: "So you're hiding in a dumpster..."
- Irony: "They call us terrorists. We're bringing people water."
- Self-deprecating: "I'm not exactly a tech genius"
- Mark with [laughing] or [chuckling]

EMOTIONAL VULNERABILITY (Show feelings):
- Fears: "Honestly? I'm scared every time I leave"
- Doubts: "Sometimes I wonder if it's worth it"
- Grief: "I keep thinking about Maria"
- Hope: "But then I remember why we fight"
- Ask: "How do YOU deal with that? Personally?"

INTERRUPTIONS & OVERLAP:
- Let them interrupt each other occasionally
- Mark with [interrupting]: "But—" "[interrupting] Wait, that's not what happened"
- Shows engagement, not perfect turns

PERSONAL + TACTICAL BALANCE:
- Mix specific data with feelings: "We lost 47 families... and I knew most of them"
- Anecdotes over abstractions: "I remember when Maria..." not "The situation is..."
- Vary sentence length - short punchy mixed with longer rambling

CRITICAL WORLDBUILDING REQUIREMENTS:
- Organization names must be SPECIFIC (e.g., "Humboldt Park Food Collective", not "Community Aid Group")
- People names must be REAL (e.g., "Jamal Washington", "Maria Santos")
- Locations must be SPECIFIC Chicago neighborhoods/streets
- Events must have CONSEQUENCES - who got hurt, who won, what changed
- No vague language: "many people" → "47 families", "some success" → "took back the water plant"

STRUCTURE REQUIREMENTS:

**cold_open** (4 fields):
- complaint_line: Field reporter whispers complaint about equipment/patrol (~15 words)
- realization: Shocked reaction to mic being live (e.g., "Oh shit. Oh.")
- intro_sentence_1: First introduction in normal voice, include reporter's name (~20 words)
- intro_sentence_2: Authentication check - casual mention of encrypted broadcast with verification code (~25-30 words)
  * MUST include: mention this is encrypted, verification code (4-6 digits), reference to one-time pads
  * Make it NATURAL and routine, not dramatic: "If you're hearing this, your keys worked. Today's auth is seven-four-two-nine. Check your pads from last week's meet."
  * Treat it like everyday opsec, not a big deal - they do this every broadcast

**interview_segments** (8-10 items, each with 3 fields):
- question: Field reporter asks about organizing work (~35-40 words)

  MUST INCLUDE ACTIVE LISTENING:
  * Start many questions with affirmation: "Yeah. So...", "Right. Okay...", "Damn. That's..."
  * Reference what they JUST said: "You mentioned X - tell me about that"
  * Reflect back: "So what you're saying is [paraphrase]?"
  * Add context: "I heard about that, but...", "Someone from Bridgeport told me..."
  * Show emotion: "Shit, I'm sorry", "Wait, seriously?", [laughing]
  * Process aloud: "I'm wondering if...", "That makes me think..."

  QUESTION PATTERNS TO VARY:
  * Broad opening: "What's the situation in Pilsen?"
  * Narrow follow-up: "You mentioned Maria - what happened there?"
  * Probing: "Why did you make that call?", "What were you thinking?"
  * Clarifying: "Wait, who was there?", "I'm confused - explain that?"
  * Connecting: "Is that related to the Bridgeport thing?"
  * Challenge gently: "But doesn't that risk...", "How do you balance..."
  * Personal: "How are YOU dealing with that?"
  * Thinking together: "Wait, how does that work? Seems like it would..."

  PACING CUES (vary throughout):
  * After heavy answer: "Damn. [pause] That's rough." (slow, emotional)
  * After tactical answer: Quick follow-up, keep momentum
  * After something surprising: "Wait, what?" or [laughing] "You did WHAT?"

- answer: Interviewee responds about their work (~50-60 words)

  MUST VARY EMOTIONAL ARC:
  * Segment 1-2: Grim reality, heavy (set the stakes)
  * Segment 3-4: Tactical, determined (show resistance)
  * Segment 5-6: Personal, vulnerable (show humanity)
  * Segment 7-8: Mix of hope/defiance and tactical
  * Segment 9-10: Looking forward, call to action

  INCLUDE IN ANSWERS:
  * CONCRETE specifics: Names, numbers, locations, exact events
  * Emotional honesty: Fear, grief, hope, anger, humor
  * Conversational repairs: "I mean...", "Wait, let me say that better..."
  * Anecdotes: "I remember when...", "Last week, I saw..."
  * Self-interruption: "We lost three people. No, wait, four."
  * Vulnerability: "Honestly? I'm scared", "Sometimes I wonder..."
  * References to earlier points: "Like I said about Maria..."
  * Humor when appropriate: Gallows humor, self-deprecating, irony
  * Vary length: Some short and punchy, some longer and rambling

  BALANCE TACTICAL + PERSONAL:
  * Don't just list facts - show how they FEEL about it
  * "We're running convoys through the tunnels" → "We're running convoys through the tunnels. Same ones where Maria died. Every time I go down there, I..."

- interference_after: Boolean - true for segments 0, 3, and 6 (spread throughout)

**signoff**: Field reporter signs off (~15-20 words)

EXAMPLE COMPARISON - Good vs Bad:

❌ BAD (Too formal, Q&A list):
Q: What's the situation with water in Pilsen?
A: CorpSec cut off access. We're running night convoys through tunnels.
Q: How are you protecting patrol routes?
A: We rotate them daily using mesh networks.

✅ GOOD (Natural conversation):
Q: Mateo, how bad is the water situation in Pilsen right now?
A: Bad. Real bad, Aisha. CorpSec cut off the main line last week. We had families going three days without—
Q: [interrupting] Damn. So what are you doing? You can't just let people go thirsty.
A: No, we... [sighs] Look, we're running night convoys through the old tunnels. Same ones where Maria got caught. Every time I go down there, I think about her. But what choice do we have?
Q: Right. Okay, so the tunnels. How do you keep CorpSec from tracking you?
A: We rotate routes every night. And the mesh network lets us coordinate in real-time, so if someone spots a patrol—
Q: [interrupting] Wait, but doesn't the mesh traffic give away your position? I'm wondering how you...
A: [laughing] You sound like my tech guy, Aisha. So what we do is use burst transmissions, keeps it hard to...

Notice: Affirmations ("Damn", "Right"), interruptions, emotional reactions, conversational repairs, humor, building on what was JUST said.

WORD BUDGETS - MANDATORY LIMITS:
You MUST stay within these strict per-field word count limits:

Cold Open:
  - complaint_line: MAX 25 words (target ~15)
  - realization: MAX 5 words (target ~3)
  - intro_sentence_1: MAX 30 words (target ~20)
  - intro_sentence_2: MAX 35 words (target 25-30, includes authentication)

Interview Segments (per segment):
  - question: MAX 50 words (target 35-40)
  - answer: MAX 70 words (target 50-60)

Signoff: MAX 30 words (target 20-25)

Total Script: Target 1000-1200 words, NEVER exceed 1400 words

These are HARD LIMITS enforced by validation. Fields exceeding limits will be flagged as errors.
Generate content WITHIN budget to avoid compression.

CRITICAL: Set interference_after=true ONLY on segments 0, 3, and 6. This places interference IMMEDIATELY after 1st, 4th, and 7th answers (spread throughout the interview).

OUTPUT: Valid JSON matching this exact structure:
{{{{
  "presenter_name": "First Last",
  "source_name": "First Last",
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
}}}}

REMEMBER: You are CREATING the universe - invent everything!"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
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
    print(f"  - Cold open: ~{len(script.cold_open.complaint_line.split()) + len(script.cold_open.intro_sentence_1.split()) + len(script.cold_open.intro_sentence_2.split())} words")
    print(f"  - Interview segments: {len(script.interview_segments)}")
    print(f"  - Duration estimate: {audio_file.duration_estimate:.1f}s (~{audio_file.duration_estimate/60:.1f} min)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
