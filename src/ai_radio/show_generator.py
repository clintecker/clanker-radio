"""Show generation pipeline orchestration."""
import json
import logging
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from google import genai

from .config import config
from .voice_synth import AudioFile
from .ingest import ingest_audio_file
from .show_models import ShowStatus, ShowFormat

logger = logging.getLogger(__name__)


def research_topics(topic_area: str, content_guidance: str = "") -> List[str]:
    """Research current topics for a show.

    Args:
        topic_area: General topic area (e.g., "Bitcoin news")
        content_guidance: Optional specific topics/angles

    Returns:
        List of topic strings suitable for show discussion

    Raises:
        ValueError: If inputs are invalid or response is malformed
        RuntimeError: If API call fails
    """
    # Input validation
    if not topic_area or not topic_area.strip():
        raise ValueError("Cannot research topics without a topic area")

    if len(topic_area) > 500:
        raise ValueError("Topic area too long (max 500 characters)")

    if content_guidance and len(content_guidance) > 1000:
        raise ValueError("Content guidance too long (max 1000 characters)")

    # API key validation
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    logger.debug(f"Starting topic research for: {topic_area[:100]}...")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Add world-building context
        world_context = f"""
WORLD SETTING: {config.world.world_setting}
TONE: {config.world.world_tone}
FRAMING: {config.world.world_framing}
"""

        prompt = f"""You are researching topics for an 8-minute radio show broadcasting from a pirate radio station.

{world_context}

Topic Area: {topic_area}
{f'Content Guidance: {content_guidance}' if content_guidance else ''}

Research and return 3-5 topics that FIT THIS FICTIONAL UNIVERSE.
These are NOT real news - you are creating plausible-sounding but fictional developments that match the dystopian, absurdist tone.
Think: corporate nightmares, AI surveillance gone wrong, tech feudalism, resistance movements.

Return ONLY a JSON array of strings (no markdown, no explanation):
["Topic 1 description", "Topic 2 description", ...]

Be specific and concrete. Each topic should be a complete sentence.
Make it feel like news FROM this wasteland, not news ABOUT technology."""

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        # Extract JSON from response
        text = response.text.strip()
        if text.startswith("```"):
            # Remove markdown code blocks
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        topics = json.loads(text.strip())

        # Validate response structure
        if not isinstance(topics, list):
            raise ValueError("Response is not a list")

        if len(topics) == 0:
            raise ValueError("No topics returned")

        if not all(isinstance(t, str) for t in topics):
            raise ValueError("Not all topics are strings")

        logger.info(f"Researched {len(topics)} topics for '{topic_area}': {topics}")
        return topics

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        raise ValueError(f"Invalid JSON response from Gemini: {e}")
    except ValueError:
        # Re-raise ValueError from validation
        raise
    except Exception as e:
        logger.exception("Topic research failed")
        raise RuntimeError(f"Failed to research topics: {e}")


def generate_interview_script(topics: List[str], personas: List[Dict[str, str]]) -> str:
    """Generate interview-format radio script.

    Args:
        topics: List of topic strings to cover
        personas: List of persona dicts with 'name' and 'traits' keys
                  First persona is the host, second is the expert

    Returns:
        Generated script with [speaker: Name] tags

    Raises:
        ValueError: If inputs are invalid or response format is wrong
        RuntimeError: If API call fails
    """
    # API key validation (check first so tests can verify this error)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not topics or len(topics) == 0:
        raise ValueError("Cannot generate script without topics")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot generate script without personas")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Safely access personas with default fallback for test scenarios
        host = personas[0] if len(personas) > 0 else {"name": "Host", "traits": "engaging"}
        expert = personas[1] if len(personas) > 1 else {"name": "Expert", "traits": "knowledgeable"}
        topics_text = "\n".join([f"- {topic}" for topic in topics])

        # Add world-building context
        world_context = f"""
WORLD SETTING: {config.world.world_setting}
TONE: {config.world.world_tone}
FRAMING: {config.world.world_framing}

This is a pirate radio broadcast FROM the ruins. The topics below are fictional developments in this dystopian world.
The hosts are survivors broadcasting truth (or their version of it) from the wasteland.
Mix dark humor with genuine information sharing. This isn't cosplay - this IS their reality.
"""

        prompt = f"""Generate an 8-minute interview-style radio dialogue (~1,200 words).

{world_context}

PERSONAS:
- Host: {host['name']} - {host['traits']}
- Expert: {expert['name']} - {expert['traits']}

TOPICS TO COVER (fictional developments in this dystopian world):
{topics_text}

OUTPUT FORMAT - Use speaker aliases AND add emotion/performance tags:
[speaker: {host['name']}] [excited] Opening dialogue here...
[speaker: {expert['name']}] [weary] Response with emotion tags...

EMOTION TAGS to use naturally throughout (don't overuse, be selective):
- [sarcastic] - for dark humor and irony
- [concerned] - when discussing serious threats
- [excited] - for interesting developments
- [weary] - when discussing exhausting dystopian reality
- [resigned] - acceptance of the wasteland
- [defiant] - resistance spirit

Use these tags sparingly - maybe 2-3 times per speaker across the whole script.

STRUCTURE:
1. Host opens with welcoming the expert and introducing the first topic
2. Expert provides detailed answer (with dystopian context)
3. Host asks follow-up question
4. Continue Q&A pattern through all topics
5. Host thanks the expert and closes

CONSTRAINTS:
- Exactly 1,200 words (±50 words)
- Natural Q&A flow: question → answer → follow-up
- Dark humor, resilient spirit, broadcasting from the ruins
- End with host thanking expert
- Use the EXACT speaker format shown above

Generate the dialogue now:"""

        logger.debug(f"Generating interview script with topics: {topics}")

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        script = response.text.strip()

        # Validate response format
        if "[speaker:" not in script:
            raise ValueError("No speaker tags found in response")

        logger.info(f"Generated interview script: {len(script)} characters")
        return script

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.exception("Interview script generation failed")
        raise RuntimeError(f"Failed to generate interview script: {e}")


def generate_discussion_script(topics: List[str], personas: List[Dict[str, str]]) -> str:
    """Generate two-host discussion format script.

    Args:
        topics: List of topic strings to cover
        personas: List of persona dicts with 'name' and 'traits' keys
                  Both personas are co-equal hosts (not host/expert)

    Returns:
        Generated script with [speaker: Name] tags

    Raises:
        ValueError: If inputs are invalid or response format is wrong
        RuntimeError: If API call fails
    """
    # API key validation (check first so tests can verify this error)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not topics or len(topics) == 0:
        raise ValueError("Cannot generate script without topics")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot generate script without personas")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Both personas are co-equal hosts (not host/expert dynamic)
        host_a = personas[0] if len(personas) > 0 else {"name": "Host A", "traits": "engaging"}
        host_b = personas[1] if len(personas) > 1 else {"name": "Host B", "traits": "thoughtful"}
        topics_text = "\n".join([f"- {topic}" for topic in topics])

        # Add world-building context
        world_context = f"""
WORLD SETTING: {config.world.world_setting}
TONE: {config.world.world_tone}
FRAMING: {config.world.world_framing}

This is a pirate radio broadcast FROM the ruins. The topics below are fictional developments in this dystopian world.
The hosts are survivors broadcasting truth (or their version of it) from the wasteland.
Mix dark humor with genuine information sharing. This isn't cosplay - this IS their reality.
"""

        prompt = f"""Generate an 8-minute discussion-style radio dialogue (~1,200 words).

{world_context}

PERSONAS (both are CO-EQUAL hosts, not host/expert):
- Host A: {host_a['name']} - {host_a['traits']}
- Host B: {host_b['name']} - {host_b['traits']}

TOPICS TO COVER (fictional developments in this dystopian world):
{topics_text}

OUTPUT FORMAT - Use speaker aliases AND add emotion/performance tags:
[speaker: {host_a['name']}] [excited] Opening argument...
[speaker: {host_b['name']}] [skeptical] Counter-argument...

EMOTION TAGS to use naturally throughout (don't overuse, be selective):
- [sarcastic] - for dark humor and irony
- [concerned] - when discussing serious threats
- [excited] - for interesting developments
- [skeptical] - challenging the other's viewpoint
- [resigned] - acceptance of the wasteland
- [defiant] - resistance spirit
- [frustrated] - when debating intensifies

Use these tags sparingly - maybe 2-3 times per speaker across the whole script.

STRUCTURE:
1. {host_a['name']} opens with topic overview
2. {host_b['name']} presents a contrasting perspective
3. Back-and-forth debate with genuine disagreement
4. {host_b['name']} closes with synthesis

CRITICAL REQUIREMENTS:
- Create genuine disagreement and contrasting viewpoints
- Avoid "I agree" or "great point" filler
- No one-sided validation - they should challenge each other
- Both hosts are equals debating ideas, not interviewing
- Natural conversational flow with back-and-forth exchanges
- Dark humor, resilient spirit, broadcasting from the ruins
- End with {host_b['name']} synthesizing the discussion

CONSTRAINTS:
- Exactly 1,200 words (±50 words)
- Must be under 7,500 bytes total
- Use the EXACT speaker format shown above

Generate the dialogue now:"""

        logger.debug(f"Generating discussion script with topics: {topics}")

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        script = response.text.strip()

        # Validate response format
        if "[speaker:" not in script:
            raise ValueError("No speaker tags found in response")

        logger.info(f"Generated discussion script: {len(script)} characters")
        return script

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.exception("Discussion script generation failed")
        raise RuntimeError(f"Failed to generate discussion script: {e}")


def generate_field_report_script(topics: List[str], personas: List[Dict[str, str]]) -> str:
    """Generate field report style radio script.

    Args:
        topics: List of civic groups/movements to cover
        personas: List of persona dicts - first is field reporter, rest are interviewees/witnesses

    Returns:
        Generated script with [speaker: Name] tags

    Raises:
        ValueError: If inputs are invalid or response is malformed
        RuntimeError: If API call fails
    """
    # Input validation
    if not topics or len(topics) == 0:
        raise ValueError("Cannot generate field report without topics")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot generate field report without personas")

    # API key validation
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    try:
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        reporter = personas[0] if len(personas) > 0 else {"name": "Reporter", "traits": "field journalist"}
        sources = personas[1:] if len(personas) > 1 else []

        topics_text = "\n".join([f"- {topic}" for topic in topics])

        # Add world-building context
        world_context = f"""
WORLD SETTING: {config.world.world_setting}
TONE: {config.world.world_tone}
FRAMING: {config.world.world_framing}

This is a field report from a pirate radio journalist embedded with resistance/civic groups.
The reporter is out in the ruins, talking to organizers, mutual aid workers, and resistance fighters.
This is grassroots journalism from the streets - raw, urgent, real.
"""

        source_personas = "\n".join([f"- {s['name']} - {s['traits']}" for s in sources]) if sources else "- Various community members (make up 2-3 names and roles)"

        prompt = f"""Generate an 8-minute field report style radio segment (~1,200 words).

{world_context}

FIELD REPORTER:
- {reporter['name']} - {reporter['traits']}

SOURCES/INTERVIEWEES TO INCLUDE:
{source_personas}

GROUPS/MOVEMENTS TO COVER:
{topics_text}

OUTPUT FORMAT - Use speaker tags AND emotion tags:
[speaker: {reporter['name']}] [urgent] Opening from the field...
[speaker: Local Organizer] [defiant] Quote from source...

EMOTION TAGS (use sparingly):
- [urgent] - breaking news energy
- [defiant] - resistance spirit
- [weary] - exhaustion from struggle
- [hopeful] - moments of solidarity
- [concerned] - real threats
- [determined] - organizing resolve

STRUCTURE:
1. Reporter opens from a specific location in the ruins/wasteland
2. Brief context on why they're there
3. Interview/quotes from 2-3 different sources from different groups
4. Reporter provides connective tissue between sources
5. Close with what's happening next / call to action

CRITICAL REQUIREMENTS:
- Feels like BEING THERE - specific locations, sounds, details
- Real voices from the movement - let sources speak in their own words
- Reporter is documenting, not editorializing
- Raw, immediate, urgent energy
- End with concrete next steps or upcoming actions
- Exactly 1,200 words (±50 words)

Generate the field report now:"""

        logger.debug(f"Generating field report script with topics: {topics}")

        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        script = response.text.strip()

        # Validate response format
        if "[speaker:" not in script:
            raise ValueError("No speaker tags found in response")

        word_count = len(script.split())
        if word_count < 800 or word_count > 1500:
            logger.warning(f"Field report length unusual: {word_count} words (target: 1200)")

        logger.info(f"Generated field report script: {len(script)} characters, {word_count} words")

        return script

    except ValueError:
        raise
    except RuntimeError:
        raise
    except Exception as e:
        logger.exception("Field report script generation failed")
        raise RuntimeError(f"Failed to generate field report script: {e}")


def extract_word_timestamps_with_whisper(audio_path: Path) -> list[dict]:
    """Extract word-level timestamps from audio using Whisper.

    Args:
        audio_path: Path to audio file

    Returns:
        List of dicts with 'word', 'start', 'end' timestamps
        Example: [{'word': 'Hello', 'start': 0.5, 'end': 0.8}, ...]
    """
    import whisper
    import json

    try:
        logger.info(f"Running Whisper STT on {audio_path}...")

        # Load model (base is good balance of speed/accuracy)
        model = whisper.load_model("base")

        # Transcribe with word timestamps
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            language="en"
        )

        # Extract word-level timestamps
        words = []
        for segment in result.get('segments', []):
            for word_info in segment.get('words', []):
                words.append({
                    'word': word_info['word'].strip(),
                    'start': word_info['start'],
                    'end': word_info['end']
                })

        logger.info(f"Extracted {len(words)} words with timestamps")
        return words

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise


def find_exact_phrase_timestamps(
    word_timestamps: list[dict],
    acknowledgment_phrases: list[dict],
    threshold: int = 85
) -> list[dict]:
    """Find exact timestamps of acknowledgment phrases using fuzzy matching.

    Args:
        word_timestamps: Word-level timestamps from Whisper STT
                        Format: [{'word': 'Hello', 'start': 0.0, 'end': 0.5}, ...]
        acknowledgment_phrases: Phrases to find with metadata
                               Format: [{'phrase': 'Nice try corps', 'timestamp': None, 'follows_segment': 1}, ...]
        threshold: Fuzzy match similarity threshold (0-100, default 85)

    Returns:
        Updated acknowledgment_phrases list with timestamps filled in where found
    """
    import re
    from thefuzz import fuzz

    def clean_text(text: str) -> str:
        """Strip emotion tags and punctuation, lowercase."""
        # Remove emotion tags [emotion]
        text = re.sub(r'\[.*?\]', '', text)
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Lowercase and collapse whitespace
        text = ' '.join(text.lower().split())
        return text

    # Build list of cleaned words with timestamps
    transcript_words = []
    for w in word_timestamps:
        cleaned_word = clean_text(w['word'])
        if cleaned_word:  # Skip empty strings after cleaning
            transcript_words.append({
                'word': cleaned_word,
                'start': w['start'],
                'end': w['end']
            })

    # Process each acknowledgment phrase with sequential search
    # This prevents matching the same occurrence twice when phrases repeat
    result = []
    search_start_time = 0.0  # Start searching from beginning for first phrase

    for ack in acknowledgment_phrases:
        # Clean the phrase
        clean_phrase = clean_text(ack['phrase'])
        phrase_words = clean_phrase.split()
        phrase_len = len(phrase_words)

        if phrase_len == 0:
            logger.warning(f"Empty phrase after cleaning: {ack['phrase']}")
            result.append(ack.copy())
            continue

        # Search for phrase with flexible N±1 word window
        min_window = max(1, phrase_len - 1)
        max_window = phrase_len + 1

        best_match = None
        best_score = 0
        best_start_idx = -1

        # Sequential search: Only search starting from search_start_time
        # This prevents matching earlier occurrences that were already matched
        for i in range(len(transcript_words)):
            # Skip words before search_start_time
            if transcript_words[i]['start'] < search_start_time:
                continue

            for window_size in range(min_window, max_window + 1):
                if i + window_size > len(transcript_words):
                    break

                # Extract window
                window_words = [transcript_words[j]['word'] for j in range(i, i + window_size)]
                window_text = ' '.join(window_words)

                # Fuzzy match
                score = fuzz.ratio(clean_phrase, window_text)

                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = window_text
                    best_start_idx = i

        # Update phrase with timestamp if found
        if best_match is not None:
            timestamp = transcript_words[best_start_idx]['start']
            result.append({
                **ack,
                'timestamp': timestamp
            })
            logger.debug(
                f"Found phrase '{ack['phrase'][:50]}...' at {timestamp:.2f}s "
                f"(score: {best_score}%, matched: '{best_match}')"
            )
            # Move search window forward: start next search 2s after this match
            # This prevents matching the same phrase twice
            search_start_time = timestamp + 2.0
        else:
            # Phrase not found - keep timestamp as None
            logger.warning(
                f"Could not find phrase '{ack['phrase'][:50]}...' in transcript "
                f"(threshold: {threshold}%)"
            )
            result.append(ack.copy())
            # Don't advance search_start_time since we didn't find this phrase

    return result


def identify_interference_points_with_llm(
    word_timestamps: list[dict],
    script_text: str
) -> list[float]:
    """Use LLM to identify precise timestamps for interference injection.

    Args:
        word_timestamps: Word-level timestamps from Whisper
        script_text: Original script text for context

    Returns:
        List of timestamps (in seconds) where interference should be placed
    """
    import google.genai as genai
    import json

    try:
        # Format transcript with timestamps for LLM
        formatted_lines = []
        for i, word_data in enumerate(word_timestamps):
            formatted_lines.append(
                f"{word_data['start']:.2f}s: {word_data['word']}"
            )

        transcript_text = "\n".join(formatted_lines)

        prompt = f"""Analyze this timestamped transcript from a pirate radio show.
The presenter acknowledges signal interference/jamming at certain moments.

Your task: Identify the EXACT timestamps where interference should be placed.
The interference should occur 0.5-1.0 seconds BEFORE the acknowledgment phrase.

Common acknowledgment phrases:
- "sorry about that" / "sorry"
- "can you still hear me" / "hear me"
- "signal's spotty" / "signal's weak" / "signal's cutting"
- "damn corp jammers" / "damn jammers"
- "where was I" / "where was i"
- "hold on" (when referring to signal issues)
- "someone's trying to jam" / "trying to jam us"
- "let me adjust" (the signal)

TIMESTAMPED TRANSCRIPT:
{transcript_text}

ORIGINAL SCRIPT (for context):
{script_text}

Output ONLY a JSON array of timestamps (in seconds) where interference should start.
Each timestamp should be 0.5-1.0 seconds BEFORE the acknowledgment phrase begins.

Example output format:
[45.2, 125.8, 230.5]

JSON array:"""

        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        logger.info("Asking LLM to identify interference injection points...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.0,  # Deterministic
                response_mime_type="application/json"
            )
        )

        # Parse JSON response
        interference_times_raw = json.loads(response.text)

        if not isinstance(interference_times_raw, list):
            logger.warning(f"LLM returned non-list: {interference_times_raw}")
            return []

        # Convert all timestamps to floats and validate
        interference_times = []
        for t in interference_times_raw:
            try:
                timestamp = float(t)
                if timestamp >= 0:
                    interference_times.append(timestamp)
                else:
                    logger.warning(f"Ignoring negative timestamp: {timestamp}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Ignoring invalid timestamp '{t}': {e}")

        logger.info(f"LLM identified {len(interference_times)} interference points: {interference_times}")
        return interference_times

    except Exception as e:
        logger.error(f"LLM interference identification failed: {e}")
        return []


def add_radio_effects(
    input_audio: Path,
    output_path: Path,
    script_text: str = None,
    interference_metadata: dict = None,
    interference_probability: float = 0.08,  # 8% chance per 10s segment if no script
    add_base_effects: bool = True,
    use_stt_timing: bool = True  # Use Whisper STT for precise timing (vs word-count estimation)
) -> None:
    """Add pirate radio authenticity - bandpass filter, noise, synced interference.

    Args:
        input_audio: Clean voice audio
        output_path: Output with radio effects
        script_text: Script text to parse for acknowledgment cues (optional, for fallback)
        interference_metadata: Metadata from renderer with acknowledgment phrases (preferred)
                              Format: {'acknowledgment_phrases': [{'phrase': 'Nice try corps', 'timestamp': None}, ...]}
        interference_probability: Chance of interference per 10-second chunk (if no script)
        add_base_effects: Add bandpass filter and light background noise
        use_stt_timing: Use Whisper STT for precise timing (vs word-count estimation)

    Effects applied:
        1. Base radio effect: bandpass filter (300-3400 Hz) + pink noise
        2. Synced interference: placed RIGHT BEFORE acknowledgment lines in script
           (or random if no script provided)
    """
    import random
    import subprocess
    import re

    try:
        # Get audio duration
        probe_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(input_audio)],
            capture_output=True, text=True, check=True
        )
        duration = float(probe_result.stdout.strip())

        # Generate interference timestamps
        interference_times = []

        if interference_metadata and 'acknowledgment_phrases' in interference_metadata:
            # Preferred: Exact phrase matching using metadata from renderer
            try:
                acknowledgment_phrases = interference_metadata['acknowledgment_phrases']
                logger.info(f"Using deterministic timing with {len(acknowledgment_phrases)} acknowledgment phrases from metadata...")

                # Step 1: Extract word-level timestamps with Whisper
                word_timestamps = extract_word_timestamps_with_whisper(input_audio)

                # Step 2: Find exact phrases using sequential search
                phrases_with_times = find_exact_phrase_timestamps(
                    word_timestamps,
                    acknowledgment_phrases
                )

                # Step 3: Place interference 0.5-1s BEFORE each phrase
                for phrase_data in phrases_with_times:
                    if phrase_data.get('timestamp') is not None:
                        interference_time = max(0, phrase_data['timestamp'] - random.uniform(0.5, 1.0))
                        interference_times.append(interference_time)
                        logger.debug(
                            f"Placing interference at {interference_time:.2f}s "
                            f"(before phrase '{phrase_data['phrase'][:30]}...' at {phrase_data['timestamp']:.2f}s)"
                        )
                    else:
                        logger.warning(f"Could not place interference for unmatched phrase: {phrase_data['phrase'][:50]}...")

                logger.info(
                    f"Deterministic timing: {len(interference_times)} interference points from "
                    f"{len(acknowledgment_phrases)} acknowledgment phrases"
                )

            except Exception as e:
                logger.error(f"Deterministic timing failed, falling back to LLM: {e}")
                # Fall through to LLM fallback
                interference_metadata = None

        if not interference_times and script_text and use_stt_timing:
            # Fallback: STT-based precise timing using Whisper + LLM
            try:
                logger.info("Using STT-based interference timing (Whisper + LLM fallback)...")

                # Step 1: Extract word-level timestamps with Whisper
                word_timestamps = extract_word_timestamps_with_whisper(input_audio)

                # Step 2: Use LLM to identify interference injection points
                interference_times = identify_interference_points_with_llm(
                    word_timestamps,
                    script_text
                )

                logger.info(f"STT-based timing: {len(interference_times)} interference bursts identified")

            except Exception as e:
                logger.error(f"STT-based timing failed, falling back to word-count estimation: {e}")
                # Fall back to word-count estimation on error
                use_stt_timing = False

        if not interference_times and script_text and not use_stt_timing:
            # Word-count estimation fallback
            logger.info("Using word-count estimation for interference timing...")

            acknowledgment_patterns = [
                r"sorry about that",
                r"can you still hear me",
                r"signal'?s?\s+(spotty|weak|cutting|struggling)",
                r"hold on",
                r"damn\s+\w*\s*jammer",
                r"someone'?s?\s+trying to jam",
                r"let me adjust",
                r"where was i"
            ]

            # Remove emotion tags to count actual words
            clean_script = re.sub(r'\[.*?\]', '', script_text)
            words = clean_script.split()
            total_words = len(words)

            logger.info(f"Parsing script: {total_words} words, {duration:.1f}s audio")

            # Find acknowledgment positions
            for pattern in acknowledgment_patterns:
                for match in re.finditer(pattern, script_text, re.IGNORECASE):
                    # Count words before this match
                    text_before = re.sub(r'\[.*?\]', '', script_text[:match.start()])
                    words_before = len(text_before.split())

                    # Estimate timestamp based on word position
                    estimated_time = (words_before / total_words) * duration

                    # Place interference 0.5-1.5s BEFORE the acknowledgment
                    interference_time = max(0, estimated_time - random.uniform(0.5, 1.5))
                    interference_times.append(interference_time)

                    logger.debug(f"Found '{match.group()}' at word {words_before}/{total_words} (~{estimated_time:.1f}s) - placing interference at {interference_time:.1f}s")

            logger.info(f"Word-count estimation: {len(interference_times)} interference bursts identified")

        if not interference_times:
            # Random interference (final fallback if all methods failed or no script/metadata provided)
            logger.info("No interference timing available, using random placement...")
            for t in range(0, int(duration), 10):
                if random.random() < interference_probability:
                    interference_times.append(t + random.uniform(0, 8))

            logger.info(f"Random {len(interference_times)} interference bursts over {duration:.1f}s")

        # Build filter chain
        filters = []

        if add_base_effects:
            # Base radio effect: bandpass (AM radio range) + boost voice + ambient transmission effects
            filters.append(
                # Bandpass filter for radio character (300-3400 Hz)
                "highpass=f=300,"
                "lowpass=f=3400,"
                # Subtle continuous vibrato for signal drift (frequency ~1.5Hz, depth ~0.05)
                "vibrato=f=1.5:d=0.05,"
                # Slight tremolo for signal strength variation (frequency ~2Hz, depth ~0.15)
                "tremolo=f=2:d=0.15,"
                # Strong boost to compensate for bandpass loss and make voice prominent
                "volume=2.5"
            )

        # Add interference as HAM radio effects overlapping with voice
        interference_filters = []
        if interference_times:
            # Build complex HAM radio interference for each burst
            interference_segments = []

            for i, t in enumerate(interference_times):
                burst_duration = random.uniform(1.5, 4.0)  # 1.5-4s bursts (longer, more impactful)

                # Combine 2-3 interference types per burst for complexity
                num_effects = random.choice([2, 3])
                effect_types = random.sample([
                    'heterodyne', 'sweep', 'digital', 'static',
                    'phasing', 'chorus', 'harmonic', 'stutter'
                ], num_effects)

                # Vary burst intensity - mix of subtle, medium, strong
                intensity = random.choice(['subtle', 'medium', 'strong'])
                intensity_ranges = {
                    'subtle': (0.5, 0.8),
                    'medium': (1.2, 1.8),
                    'strong': (2.0, 3.0)
                }

                # Each effect gets its own flutter/warble
                for effect_type in effect_types:
                    # Random flutter for this effect
                    effect_flutter_freq = random.uniform(3, 15)
                    effect_flutter_depth = random.uniform(0.6, 0.9)
                    vol_min, vol_max = intensity_ranges[intensity]
                    base_volume = random.uniform(vol_min, vol_max)

                    if effect_type == 'heterodyne':
                        # Howling/beating tones (classic HAM radio interference)
                        freq1 = random.uniform(800, 2000)
                        freq2 = freq1 + random.uniform(5, 50)  # Close frequencies create beating
                        interference_segments.append({
                            'type': 'heterodyne',
                            'start': t,
                            'duration': burst_duration,
                            'freq1': freq1,
                            'freq2': freq2,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'sweep':
                        # Swirling frequency sweep
                        start_freq = random.uniform(400, 1000)
                        end_freq = random.uniform(1500, 3000)
                        interference_segments.append({
                            'type': 'sweep',
                            'start': t,
                            'duration': burst_duration,
                            'start_freq': start_freq,
                            'end_freq': end_freq,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'digital':
                        # Multiple overlapping tones (like modem/digital interference)
                        freqs = [random.uniform(600, 2500) for _ in range(3)]
                        interference_segments.append({
                            'type': 'digital',
                            'start': t,
                            'duration': burst_duration,
                            'freqs': freqs,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'static':
                        # White noise static (classic)
                        interference_segments.append({
                            'type': 'static',
                            'start': t,
                            'duration': burst_duration,
                            'base_volume': base_volume * 1.5,  # Louder static
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'phasing':
                        # Phase shifter effect (swooshing)
                        freq = random.uniform(800, 1800)
                        interference_segments.append({
                            'type': 'phasing',
                            'start': t,
                            'duration': burst_duration,
                            'freq': freq,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'chorus':
                        # Chorus/thickening effect
                        freq = random.uniform(900, 1600)
                        interference_segments.append({
                            'type': 'chorus',
                            'start': t,
                            'duration': burst_duration,
                            'freq': freq,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'harmonic':
                        # Harmonic distortion (overtones)
                        base_freq = random.uniform(400, 1200)
                        harmonics = [base_freq * h for h in [1, 2, 3]]
                        interference_segments.append({
                            'type': 'harmonic',
                            'start': t,
                            'duration': burst_duration,
                            'harmonics': harmonics,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })
                    elif effect_type == 'stutter':
                        # Glitchy stuttering effect
                        freq = random.uniform(700, 1500)
                        stutter_rate = random.uniform(8, 20)  # Hz
                        interference_segments.append({
                            'type': 'stutter',
                            'start': t,
                            'duration': burst_duration,
                            'freq': freq,
                            'stutter_rate': stutter_rate,
                            'base_volume': base_volume,
                            'flutter_freq': effect_flutter_freq,
                            'flutter_depth': effect_flutter_depth
                        })

            # Store interference segments for later processing
            interference_filters = interference_segments

        # Join filters
        filter_str = ",".join(filters) if filters else "anull"

        # Build ffmpeg command with HAM radio interference effects
        if add_base_effects:
            if interference_filters:
                # Generate complex HAM radio interference
                interference_inputs = []
                interference_filter_complex = []
                input_index = 2  # Start after voice (0) and pink noise (1)

                for seg in interference_filters:
                    # Create fluttering volume envelope with warble
                    flutter_expr = f"{seg['base_volume']}+{seg['flutter_depth']}*sin(2*PI*{seg['flutter_freq']}*t)"
                    vol_expr = f"if(between(t,{seg['start']},{seg['start']+seg['duration']}),{flutter_expr},0)"

                    if seg['type'] == 'heterodyne':
                        # Two close frequencies beating against each other (howling)
                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"sine=frequency={seg['freq1']}:duration={duration}:sample_rate=48000",
                            "-f", "lavfi", "-i", f"sine=frequency={seg['freq2']}:duration={duration}:sample_rate=48000"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a][{input_index+1}:a]amix=inputs=2[het{input_index}];"
                            f"[het{input_index}]volume=volume='{vol_expr}':eval=frame[het{input_index}_env]"
                        )
                        input_index += 2

                    elif seg['type'] == 'sweep':
                        # Frequency sweep using vibrato (simpler than dynamic frequency)
                        # Use middle frequency with vibrato to create swirling effect
                        mid_freq = (seg['start_freq'] + seg['end_freq']) / 2
                        vibrato_freq = 2.0 + random.uniform(0, 2)  # Vibrato speed
                        vibrato_depth = 0.9  # Deep vibrato for sweep effect

                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"sine=frequency={mid_freq}:duration={duration}:sample_rate=48000"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a]vibrato=f={vibrato_freq}:d={vibrato_depth}[sweep{input_index}];"
                            f"[sweep{input_index}]volume=volume='{vol_expr}':eval=frame[sweep{input_index}_env]"
                        )
                        input_index += 1

                    elif seg['type'] == 'digital':
                        # Multiple overlapping tones (modem-like)
                        for freq in seg['freqs']:
                            interference_inputs.extend([
                                "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}:sample_rate=48000"
                            ])

                        # Mix the tones
                        tone_inputs = [f"[{input_index+i}:a]" for i in range(len(seg['freqs']))]
                        interference_filter_complex.append(
                            f"{''.join(tone_inputs)}amix=inputs={len(seg['freqs'])}[dig{input_index}];"
                            f"[dig{input_index}]volume=volume='{vol_expr}':eval=frame[dig{input_index}_env]"
                        )
                        input_index += len(seg['freqs'])

                    elif seg['type'] == 'static':
                        # Classic white noise
                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=white:r=48000:a=1.0"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a]volume=volume='{vol_expr}':eval=frame[stat{input_index}_env]"
                        )
                        input_index += 1

                    elif seg['type'] == 'phasing':
                        # Phase shifter effect (swooshing)
                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"sine=frequency={seg['freq']}:duration={duration}:sample_rate=48000"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a]aphaser=in_gain=0.4:out_gain=0.74:delay=3.0:decay=0.4:speed=0.5:type=t[phase{input_index}];"
                            f"[phase{input_index}]volume=volume='{vol_expr}':eval=frame[phase{input_index}_env]"
                        )
                        input_index += 1

                    elif seg['type'] == 'chorus':
                        # Chorus/thickening effect
                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"sine=frequency={seg['freq']}:duration={duration}:sample_rate=48000"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a]chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3[chorus{input_index}];"
                            f"[chorus{input_index}]volume=volume='{vol_expr}':eval=frame[chorus{input_index}_env]"
                        )
                        input_index += 1

                    elif seg['type'] == 'harmonic':
                        # Harmonic distortion (overtones)
                        for harmonic in seg['harmonics']:
                            interference_inputs.extend([
                                "-f", "lavfi", "-i", f"sine=frequency={harmonic}:duration={duration}:sample_rate=48000"
                            ])
                        # Mix the harmonics
                        harmonic_inputs = [f"[{input_index+i}:a]" for i in range(len(seg['harmonics']))]
                        interference_filter_complex.append(
                            f"{''.join(harmonic_inputs)}amix=inputs={len(seg['harmonics'])}:weights=1.0 0.5 0.3[harm{input_index}];"
                            f"[harm{input_index}]volume=volume='{vol_expr}':eval=frame[harm{input_index}_env]"
                        )
                        input_index += len(seg['harmonics'])

                    elif seg['type'] == 'stutter':
                        # Glitchy stuttering effect (rapid tremolo)
                        interference_inputs.extend([
                            "-f", "lavfi", "-i", f"sine=frequency={seg['freq']}:duration={duration}:sample_rate=48000"
                        ])
                        interference_filter_complex.append(
                            f"[{input_index}:a]tremolo=f={seg['stutter_rate']}:d=0.9[stutter{input_index}];"
                            f"[stutter{input_index}]volume=volume='{vol_expr}':eval=frame[stutter{input_index}_env]"
                        )
                        input_index += 1

                # Collect all interference streams to mix
                interference_streams = []
                for line in interference_filter_complex:
                    # Extract output label (last label in each line)
                    if '[' in line:
                        interference_streams.append(line.split('[')[-1].rstrip(']'))

                # Define consistent mixing weights for clarity and control
                voice_weight = 5.0  # Voice should dominate (increased from 2.5)
                pink_noise_weight = 0.1
                interference_weight = 0.8  # Audible but not overwhelming

                # Build voice degradation expression - voice drops/warbles during interference
                voice_degradation_parts = []
                for seg in interference_filters:
                    # During interference: duck volume slightly (still audible)
                    seg_start = seg['start']
                    seg_end = seg['start'] + seg['duration']
                    # Volume drops to 75% during interference (0.25 reduction, still audible)
                    voice_degradation_parts.append(
                        f"between(t,{seg_start},{seg_end})*0.25"
                    )

                # Voice volume expression: normal=1.0, during interference=0.75
                voice_vol_expr = "1.0-(" + "+".join(voice_degradation_parts) + ")" if voice_degradation_parts else "1.0"

                # Build full filter complex with voice degradation
                # Apply radio effects to voice, add degradation during interference, normalize, then mix
                filter_complex = (
                    f"[0:a]{filter_str}[voice_filtered];"
                    # Add pitch warble and volume duck during interference
                    f"[voice_filtered]volume=volume='{voice_vol_expr}':eval=frame,"
                    # Add subtle vibrato (pitch warble) during interference for instability
                    f"vibrato=f=5:d=0.3[voice_degraded];"
                    # Normalize the degraded voice HOT
                    f"[voice_degraded]loudnorm=I=-14:TP=-1.5:LRA=11[voice_norm];"
                    + ";".join(interference_filter_complex) + ";"
                    + f"[voice_norm][1:a]{''.join(['['+s+']' for s in interference_streams])}amix=inputs={2+len(interference_streams)}:weights={'{:.1f} {:.1f} '.format(voice_weight, pink_noise_weight) + ' '.join(['{:.1f}'.format(interference_weight)]*len(interference_streams))}[out]"
                )

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(input_audio),
                    "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=48000:a=0.015",
                    *interference_inputs,
                    "-filter_complex", filter_complex,
                    "-map", "[out]",
                    "-c:a", "libmp3lame", "-q:a", "2",
                    str(output_path)
                ]
            else:
                # Just voice + pink noise (no interference bursts)
                # Define consistent mixing weights
                voice_weight = 2.5  # Voice should dominate
                pink_noise_weight = 0.1

                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(input_audio),
                    "-f", "lavfi", "-i", f"anoisesrc=d={duration}:c=pink:r=48000:a=0.015",
                    "-filter_complex",
                    # Apply radio effects to voice, normalize it HOT, then mix with pink noise
                    f"[0:a]{filter_str},loudnorm=I=-14:TP=-1.5:LRA=11[voice_norm];"
                    f"[voice_norm][1:a]amix=inputs=2:weights={voice_weight} {pink_noise_weight}[out]",
                    "-map", "[out]",
                    "-c:a", "libmp3lame", "-q:a", "2",
                    str(output_path)
                ]
        else:
            # Just apply interference without any noise layers
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", str(input_audio),
                "-af", filter_str,
                "-c:a", "libmp3lame", "-q:a", "2",
                str(output_path)
            ]

        logger.debug(f"Radio effects command: {' '.join(ffmpeg_cmd)}")

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=600
        )

        if result.returncode != 0:
            logger.error(f"Radio effects failed: {result.stderr}")
            # Fallback: just copy input
            import shutil
            shutil.copy(input_audio, output_path)
        else:
            logger.info(f"Radio effects applied: {len(interference_times)} interference bursts")

    except Exception as e:
        logger.exception(f"Failed to add radio effects: {e}")
        # Fallback: copy input
        import shutil
        shutil.copy(input_audio, output_path)


def add_background_bed(
    voice_audio: Path,
    output_path: Path,
    intro_seconds: float = 5.0,
    outro_seconds: float = 5.5,
    ducked_volume_db: float = -20.0,  # Bed ducks down 20dB during voice (background presence)
    voice_fadein: float = 0.5,
    voice_fadeout: float = 0.5,
    bed_fadein: float = 1.0,  # Bed fades in at start
    bed_duck_transition: float = 2.0,  # How fast bed ducks down when voice starts (slower = smoother)
    bed_unduck_transition: float = 2.0,  # How fast bed ducks up when voice ends (slower = smoother)
    bed_fadeout: float = 1.0  # Bed fades out at end
) -> None:
    """Add background music bed with ducking to voice audio.

    Timing:
    - 00:00 to bed_fadein: Bed fades in
    - bed_fadein to intro_seconds: Bed at full volume
    - intro_seconds to intro_seconds+bed_duck_transition: Bed ducks down, voice fades in
    - Voice plays with ducked bed
    - voice_end-voice_fadeout to voice_end: Voice fades out, bed still ducked
    - voice_end to voice_end+bed_unduck_transition: Bed ducks back up to full
    - voice_end+bed_unduck_transition to total-bed_fadeout: Bed at full volume
    - Last bed_fadeout seconds: Bed fades out

    Args:
        voice_audio: Path to voice-only audio file
        output_path: Path for output with bed
        intro_seconds: Seconds of bed before voice (default 5.0)
        outro_seconds: Seconds of bed after voice (default 5.5)
        ducked_volume_db: Bed volume reduction in dB during voice (default -30.0)
        voice_fadein: Voice fade-in duration (default 0.5)
        voice_fadeout: Voice fade-out duration (default 0.5)
        bed_fadein: Bed fade-in at start (default 1.0)
        bed_duck_transition: Bed duck-down transition time (default 0.5)
        bed_unduck_transition: Bed duck-up transition time (default 0.5)
        bed_fadeout: Bed fade-out at end (default 1.0)

    Raises:
        RuntimeError: If ffmpeg processing fails
    """
    import math
    import random
    import shutil

    # Get a random bed from the beds directory using resolved path
    beds_dir = config.paths.beds_dir_resolved

    if beds_dir is None:
        logger.warning(
            "No background beds directory found. Checked:\n"
            f"  - $AI_RADIO_BEDS_DIR\n"
            f"  - {config.paths.beds_path}\n"
            f"  - ~/Music/radio-beds\n"
            f"  - ./assets/beds\n"
            f"  - /tmp/radio-beds\n"
            "Background music will be skipped."
        )
        shutil.copy(voice_audio, output_path)
        return

    logger.info(f"Using beds directory: {beds_dir}")

    # Find all audio files in beds directory (MP3 or WAV)
    bed_files = list(beds_dir.glob("*.mp3")) + list(beds_dir.glob("*.wav"))

    if not bed_files:
        logger.warning(f"No bed files found in {beds_dir}, skipping background music")
        shutil.copy(voice_audio, output_path)
        return

    # Select random bed
    bed_path = random.choice(bed_files)
    logger.info(f"Adding background bed: {bed_path.name}")

    # Get voice duration using ffprobe
    try:
        probe_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(voice_audio)
            ],
            capture_output=True,
            text=True,
            check=False
        )
        voice_duration = float(probe_result.stdout.strip())
    except (ValueError, subprocess.SubprocessError) as e:
        logger.error(f"Failed to get voice duration: {e}")
        shutil.copy(voice_audio, output_path)
        return

    # Calculate timing
    total_duration = intro_seconds + voice_duration + outro_seconds
    voice_end = intro_seconds + voice_duration
    bed_duck_end = intro_seconds + bed_duck_transition
    bed_unduck_end = voice_end + bed_unduck_transition
    bed_fadeout_start = total_duration - bed_fadeout

    # Convert dB to linear volume multiplier for the volume filter
    ducked_volume_linear = math.pow(10, ducked_volume_db / 20.0)

    logger.info(f"Bed timing: intro={intro_seconds}s, voice={voice_duration}s, outro={outro_seconds}s, total={total_duration}s")
    logger.info(f"Fade in: 0s-{bed_fadein}s, Duck down: {intro_seconds}s-{bed_duck_end}s, Duck up: {voice_end}s-{bed_unduck_end}s, Fade out: {bed_fadeout_start}s-{total_duration}s")

    # Correct volume expression for ducking logic.
    # Note: Commas are NOT escaped inside the expression string.
    volume_expr = (
        f"if(lt(t,{intro_seconds}),1,"  # Before voice: 1.0 (full volume)
        f"if(lt(t,{bed_duck_end}),1+({ducked_volume_linear}-1)*(t-{intro_seconds})/{bed_duck_transition},"  # Ramp down
        f"if(lt(t,{voice_end}),{ducked_volume_linear},"  # Hold ducked volume
        f"if(lt(t,{bed_unduck_end}),{ducked_volume_linear}+(1-{ducked_volume_linear})*(t-{voice_end})/{bed_unduck_transition},"  # Ramp up
        f"1))))"  # After voice: 1.0 (full volume)
    )

    # Complex filter for proper ducking, fading, and normalization:
    filter_complex = (
        # Chain 1: Process voice audio
        # Delay it, then apply fade-in and fade-out at the correct timestamps.
        f"[0:a]adelay={int(intro_seconds * 1000)}|{int(intro_seconds * 1000)},"
        f"afade=t=in:st={intro_seconds}:d={voice_fadein},"
        f"afade=t=out:st={voice_end - voice_fadeout}:d={voice_fadeout}[voice];"

        # Chain 2: Process background bed (part 1)
        # Loop the bed audio, trim it to the final total duration, and apply the main fade-in/out.
        f"[1:a]aloop=loop=-1:size=2e+09,atrim=end={total_duration},"
        f"afade=t=in:st=0:d={bed_fadein},"
        f"afade=t=out:st={bed_fadeout_start}:d={bed_fadeout}[bed_faded];"

        # Chain 3: Apply the time-based ducking volume envelope to the bed.
        f"[bed_faded]volume=volume='{volume_expr}':eval=frame[bed];"

        # Chain 4: Mix the pre-normalized voice with the ducked bed.
        # Use weights to preserve voice volume (1.0) and set the bed level (-10dB).
        # This avoids the default -6dB amix attenuation and removes the problematic final loudnorm.
        f"[voice][bed]amix=inputs=2:duration=longest:weights=1.0 0.3[out]"
    )

    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-i", str(voice_audio),      # Input 0: voice
        "-i", str(bed_path),         # Input 1: bed
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        str(output_path)
    ]

    logger.debug(f"Executing ffmpeg command: {' '.join(ffmpeg_command)}")

    try:
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,
            text=True,
            check=False,
            timeout=600
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg bed mixing failed: {result.stderr}")
            # Fallback: just copy voice audio
            shutil.copy(voice_audio, output_path)
            logger.warning("Falling back to voice-only audio")
        else:
            logger.info("Background bed added successfully with fades and ducking")

    except Exception as e:
        logger.exception(f"Failed to add background bed: {e}")
        # Fallback: just copy voice audio
        shutil.copy(voice_audio, output_path)


def synthesize_show_audio(
    script_text: str,
    personas: List[Dict[str, str]],
    output_path: Path,
    add_bed: bool = True,
    interference_metadata: dict = None
) -> Optional[AudioFile]:
    """Synthesize multi-speaker audio from script.

    Args:
        script_text: Script with [speaker: Name] tags
        personas: List of persona dicts with 'name' and 'traits' keys
        output_path: Path where audio file will be saved
        add_bed: Whether to add background music bed
        interference_metadata: Metadata from renderer with acknowledgment phrases for timing
                              Format: {'acknowledgment_phrases': [{'phrase': 'Nice try corps', 'timestamp': None}, ...]}

    Returns:
        AudioFile with metadata, or None if synthesis fails

    Raises:
        ValueError: If inputs are invalid
        RuntimeError: If synthesis fails
    """
    # API key validation (check first)
    if not config.api_keys.gemini_api_key:
        raise ValueError("RADIO_GEMINI_API_KEY not configured")

    # Input validation
    if not script_text or not script_text.strip():
        raise ValueError("Cannot synthesize empty script")

    if "[speaker:" not in script_text:
        raise ValueError("No speaker tags found in script")

    if not personas or len(personas) == 0:
        raise ValueError("Cannot synthesize without personas")

    try:
        # Extract speaker names from personas
        speaker_names = [p["name"] for p in personas]
        voice = ", ".join(speaker_names)

        logger.debug(f"Synthesizing audio for speakers: {voice}")

        # Call Gemini TTS API with multi-speaker voice configuration
        client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

        # Single speaker vs multi-speaker mode
        # CRITICAL: Gemini TTS requires EXACTLY 2 speakers for multi-speaker mode
        # For single speaker, use regular voice_config instead
        if len(personas) == 1:
            # Single speaker mode - use emotion tags with single voice
            persona = personas[0]
            traits_lower = persona.get("traits", "").lower()

            # Select voice based on gender
            if "female" in traits_lower or "woman" in traits_lower:
                voice_name = "Aoede"  # Default female voice
            elif "male" in traits_lower or "man" in traits_lower:
                voice_name = "Puck"  # Default male voice
            else:
                voice_name = "Aoede"  # Default to female

            logger.info(f"Single speaker mode: {persona['name']} using voice {voice_name}")

            response = client.models.generate_content(
                model=config.tts.gemini_tts_model,
                contents=script_text,
                config=genai.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai.types.SpeechConfig(
                        voice_config=genai.types.VoiceConfig(
                            prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
        else:
            # Multi-speaker mode - assign different voices
            # Voice genders: Aoede(F), Puck(M), Charon(M), Kore(F), Fenrir(M), Leda(F), Orus(M), Zephyr(F)
            speaker_voice_configs = []

            # Smart voice assignment based on traits
            for i, persona in enumerate(personas[:2]):  # Only first 2 personas get distinct voices
                traits_lower = persona.get("traits", "").lower()

                # Check for gender hints in traits
                if "female" in traits_lower or "woman" in traits_lower:
                    # Use female voices - rotate through them
                    female_voices = ["Aoede", "Kore", "Leda", "Zephyr"]
                    voice_name = female_voices[i % len(female_voices)]
                elif "male" in traits_lower or "man" in traits_lower:
                    # Use male voices - rotate through them
                    male_voices = ["Puck", "Charon", "Fenrir", "Orus"]
                    voice_name = male_voices[i % len(male_voices)]
                else:
                    # Default: alternate male/female
                    all_voices = ["Puck", "Aoede", "Charon", "Kore"]
                    voice_name = all_voices[i % len(all_voices)]

                speaker_voice_configs.append(
                    genai.types.SpeakerVoiceConfig(
                        speaker=persona["name"],
                        voice_config=genai.types.VoiceConfig(
                            prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )

            # Warn if there are more than 2 personas (additional speakers won't have distinct voices)
            if len(personas) > 2:
                logger.warning(f"Show has {len(personas)} personas but Gemini TTS only supports 2 distinct voices")
                logger.warning(f"Only {personas[0]['name']} and {personas[1]['name']} will have distinct voices")

            voice_mapping = ', '.join([f"{config.speaker}={config.voice_config.prebuilt_voice_config.voice_name}" for config in speaker_voice_configs])
            logger.info(f"Multi-speaker mode: {voice_mapping}")

            response = client.models.generate_content(
                model=config.tts.gemini_tts_model,
                contents=script_text,
                config=genai.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=genai.types.SpeechConfig(
                        multi_speaker_voice_config=genai.types.MultiSpeakerVoiceConfig(
                            speaker_voice_configs=speaker_voice_configs
                        )
                    )
                )
            )

        # Extract PCM audio data from response
        if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
            raise RuntimeError("No audio data in Gemini response")

        parts = response.candidates[0].content.parts
        num_parts = len(parts)

        # Log if there are multiple parts (we might be missing audio!)
        if num_parts > 1:
            logger.warning(f"TTS response has {num_parts} parts - we only use the first part!")
            logger.warning("This may cause truncated or incomplete audio")

        audio_data = parts[0].inline_data.data

        if not audio_data:
            raise RuntimeError("No audio inline_data in Gemini response")

        # Handle potential base64 encoding (known issue in some SDK versions)
        import base64
        if isinstance(audio_data, str):
            logger.info("Audio data is string (base64) - decoding to bytes")
            audio_data = base64.b64decode(audio_data)
        elif not isinstance(audio_data, bytes):
            raise RuntimeError(f"Unexpected audio data type: {type(audio_data)}")

        # Validate PCM size and log diagnostics
        pcm_size = len(audio_data)
        expected_duration = pcm_size / 48000  # 24kHz 16-bit mono = 48000 bytes/sec
        logger.info(f"TTS returned {pcm_size:,} bytes PCM audio (~{expected_duration:.1f}s)")

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write PCM data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
            pcm_file.write(audio_data)
            pcm_path = pcm_file.name

        voice_only_path = output_path  # May be replaced with temp file if adding bed
        temp_voice_file = None

        try:
            # If adding bed, create voice-only audio to temp file first
            if add_bed:
                temp_voice_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                voice_only_path = Path(temp_voice_file.name)
                temp_voice_file.close()

            # Convert PCM to MP3 using ffmpeg
            # Gemini TTS outputs 24kHz 16-bit mono PCM
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",  # Overwrite output file
                    "-f", "s16le",  # Format: signed 16-bit little-endian
                    "-ar", "24000",  # Sample rate: 24kHz
                    "-ac", "1",  # Audio channels: mono
                    "-i", pcm_path,  # Input PCM file
                    "-c:a", "libmp3lame",
                    "-q:a", "2",  # High quality MP3
                    str(voice_only_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg PCM conversion failed: {result.stderr}")
                raise RuntimeError("Failed to synthesize audio")

            # Add pirate radio effects (bandpass, interference, etc.)
            if add_bed:
                # Apply radio effects to voice before adding bed
                temp_radio_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                voice_with_effects_path = Path(temp_radio_file.name)
                temp_radio_file.close()

                logger.info("Adding pirate radio effects (bandpass, interference)...")
                add_radio_effects(
                    voice_only_path,
                    voice_with_effects_path,
                    script_text=script_text,
                    interference_metadata=interference_metadata
                )

                # Clean up voice-only temp file
                voice_only_path.unlink(missing_ok=True)

                # Add background bed with ducking
                logger.info("Adding background bed with ducking...")
                add_background_bed(voice_with_effects_path, output_path)

                # Clean up voice-with-effects temp file
                voice_with_effects_path.unlink(missing_ok=True)
            else:
                # No bed - just apply radio effects directly to output
                logger.info("Adding pirate radio effects...")
                temp_radio_output = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                radio_output_path = Path(temp_radio_output.name)
                temp_radio_output.close()

                add_radio_effects(
                    voice_only_path,
                    radio_output_path,
                    script_text=script_text,
                    interference_metadata=interference_metadata
                )

                # Move to final output
                import shutil
                shutil.move(str(radio_output_path), str(output_path))

        finally:
            # Clean up temp PCM file
            Path(pcm_path).unlink(missing_ok=True)

        # Estimate duration (150 words per minute)
        word_count = len(script_text.split())
        duration_estimate = (word_count / 150) * 60  # Convert to seconds

        logger.info(
            f"Show audio synthesis complete: {output_path} "
            f"(~{duration_estimate:.1f}s, {word_count} words, voices: {voice})"
        )

        return AudioFile(
            file_path=output_path,
            duration_estimate=duration_estimate,
            timestamp=datetime.now(),
            voice=voice,
            model=config.tts.gemini_tts_model
        )

    except ValueError:
        # Re-raise validation errors
        raise
    except RuntimeError:
        # Re-raise runtime errors
        raise
    except Exception as e:
        logger.exception("Audio synthesis failed")
        raise RuntimeError(f"Failed to synthesize audio: {e}")


class ShowGenerator:
    """Orchestrates complete show generation pipeline.

    Coordinates: research → script → audio → ingest → database updates
    Handles state machine transitions and error recovery.
    """

    def __init__(self, repository):
        """Initialize show generator.

        Args:
            repository: Repository instance with database update methods
        """
        self.repository = repository

    def generate(self, schedule, show) -> None:
        """Generate complete show from schedule.

        Orchestrates the full pipeline from research through to ready asset:
        1. Check if resuming from ShowStatus.SCRIPT_COMPLETE (skip research/script)
        2. If pending: research topics → generate script → update DB
        3. Generate audio from script
        4. Ingest audio to assets
        5. Update DB to ready with asset_id

        Args:
            schedule: ShowSchedule with format, topics, personas
            show: GeneratedShow with id, status, script_text

        State transitions:
            - pending → ShowStatus.SCRIPT_COMPLETE → ready
            - pending → script_failed (on research/script error)
            - ShowStatus.SCRIPT_COMPLETE → ready (resumption path)
            - ShowStatus.SCRIPT_COMPLETE → audio_failed (on audio error)
        """
        logger.info(f"Starting show generation for show ID {show.id} (status: {show.status})")

        try:
            # Check if resuming from script_complete state
            if show.status == ShowStatus.SCRIPT_COMPLETE:
                logger.info("Resuming from script_complete state")
                script_text = show.script_text
            else:
                # Phase 1: Research and script generation
                logger.info("Phase 1: Research and script generation")

                # Research topics
                topics = research_topics(
                    topic_area=schedule.topic_area,
                    content_guidance=schedule.content_guidance or ""
                )
                logger.info(f"Researched {len(topics)} topics")

                # Parse personas from JSON string
                personas = json.loads(schedule.personas)

                # Generate script based on format
                if schedule.format == ShowFormat.INTERVIEW:
                    script_text = generate_interview_script(
                        topics=topics,
                        personas=personas
                    )
                    logger.info("Generated interview script")
                elif schedule.format == ShowFormat.TWO_HOST_DISCUSSION:
                    script_text = generate_discussion_script(
                        topics=topics,
                        personas=personas
                    )
                    logger.info("Generated discussion script")
                elif schedule.format == ShowFormat.FIELD_REPORT:
                    script_text = generate_field_report_script(
                        topics=topics,
                        personas=personas
                    )
                    logger.info("Generated field report script")
                else:
                    raise ValueError(f"Invalid show format: {schedule.format}")

                # Update database with completed script
                self.repository.update_show_script(show.id, script_text)
                self.repository.update_show_status(show.id, ShowStatus.SCRIPT_COMPLETE)
                logger.info("Script phase complete, updated database")

        except Exception as e:
            # Script generation failed
            logger.exception(f"Script generation failed for show {show.id}")
            self.repository.update_show_status(show.id, ShowStatus.SCRIPT_FAILED)
            self.repository.update_show_error(show.id, str(e))
            return

        # Generate temp file path for audio synthesis
        output_path = config.paths.tmp_path / f"show_{show.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"

        try:
            # Phase 2: Audio synthesis
            logger.info("Phase 2: Audio synthesis")

            # Parse personas again if not already parsed (for resume path)
            personas = json.loads(schedule.personas)

            # Synthesize audio
            audio_file = synthesize_show_audio(
                script_text=script_text,
                personas=personas,
                output_path=output_path
            )

            if not audio_file:
                raise RuntimeError("Audio synthesis returned None")

            logger.info(f"Audio synthesized: {audio_file.duration_estimate:.1f}s")

            # Phase 3: Ingest audio to assets
            logger.info("Phase 3: Ingesting audio to assets")

            asset_dict = ingest_audio_file(
                source_path=audio_file.file_path,
                kind="break",
                db_path=config.paths.db_path,
                output_dir=config.paths.music_path
            )

            asset_id = asset_dict["id"]
            asset_filepath = Path(asset_dict["path"])
            logger.info(f"Audio ingested with asset ID: {asset_id}")

            # Update database with asset and mark as ready
            try:
                self.repository.update_show_asset(show.id, asset_id)
                self.repository.update_show_status(show.id, ShowStatus.READY)
                logger.info(f"Show {show.id} generation complete: ready with asset {asset_id}")
            except Exception as db_error:
                # DB update failed - cleanup orphaned asset
                logger.warning(f"DB update failed for show {show.id}. Cleaning up orphaned asset: {asset_id}")
                try:
                    # Delete file from disk
                    if asset_filepath.exists():
                        asset_filepath.unlink()
                        logger.info(f"Deleted orphaned file: {asset_filepath}")

                    # Delete from assets table
                    conn = sqlite3.connect(config.paths.db_path)
                    try:
                        conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
                        conn.commit()
                        logger.info(f"Deleted orphaned asset record: {asset_id}")
                    finally:
                        conn.close()
                except Exception as cleanup_error:
                    logger.error(
                        f"CRITICAL: Failed to cleanup orphaned asset {asset_id}: {cleanup_error}. "
                        f"Manual cleanup required for file: {asset_filepath}"
                    )
                # Re-raise original DB error
                raise db_error

        except Exception as e:
            # Audio synthesis or ingestion failed
            logger.exception(f"Audio synthesis failed for show {show.id}")
            self.repository.update_show_status(show.id, ShowStatus.AUDIO_FAILED)
            self.repository.update_show_error(show.id, str(e))
            return

        finally:
            # Always clean up temporary audio file
            if output_path.exists():
                output_path.unlink()
                logger.debug(f"Cleaned up temporary audio file: {output_path.name}")
