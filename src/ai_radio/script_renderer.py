"""Render structured scripts to final text format with programmatic interference."""
import random
import re

from ai_radio.models.script_schema import FieldReportScript


# Template phrases for interference acknowledgments (NOT model-generated)
INTERFERENCE_TEMPLATES = [
    "[nervous] Sorry about that, someone's trying to jam us again...",
    "[frustrated] Damn corp jammers... [short pause] where was I?",
    "[worried] Can you still hear me? Signal's spotty...",
    "[annoyed] Hold on... [short pause] okay, signal's back",
    "[tense] They're trying to block us... [short pause] still here",
    "[defiant] Nice try, corps. [short pause] You can't silence us."
]


# Emotion pools for questions and answers
# Richer set for dystopian resistance vibe
QUESTION_EMOTIONS = [
    "curious", "concerned", "interested", "skeptical", "worried",
    "urgent", "intense", "direct", "probing", "careful"
]
ANSWER_EMOTIONS = [
    "earnest", "passionate", "determined", "worried", "hopeful", "confident",
    "defiant", "resolute", "fierce", "steadfast", "grim", "intense"
]


# Pause variations for natural flow
PAUSES = ["[short pause]", "[medium pause]"]


def clean_phrase(phrase: str) -> str:
    """Remove emotion tags and extra punctuation from phrase.

    Args:
        phrase: Raw phrase with potential emotion tags like "[nervous] text..."

    Returns:
        Cleaned phrase without tags or trailing punctuation
    """
    # Remove all [tag] patterns
    cleaned = re.sub(r'\[.*?\]', '', phrase)

    # Normalize multiple spaces to single space
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # Strip whitespace and trailing ellipsis/punctuation
    cleaned = cleaned.strip()
    cleaned = cleaned.rstrip('.,;:!?…')

    return cleaned


def render_script(
    script: FieldReportScript,
    presenter: str,
    source: str
) -> tuple[str, dict]:
    """Render structured script to final text format with speaker tags.

    Programmatically injects interference acknowledgments from templates
    rather than relying on model generation.

    Args:
        script: The structured script to render
        presenter: Name of the presenter/reporter
        source: Name of the interview source

    Returns:
        Tuple of (rendered_script, metadata) where metadata contains:
        {
            "acknowledgment_phrases": [
                {"line_num": 5, "phrase": "Nice try, corps", "timestamp": None},
                ...
            ],
            "total_lines": 25,
            "total_words": 455
        }
    """
    lines = []
    metadata = {
        "acknowledgment_phrases": [],
        "total_lines": 0,
        "total_words": 0
    }

    # Track used templates to prevent repetition
    used_interference_phrases = []
    available_templates = list(INTERFERENCE_TEMPLATES)

    # Track last emotions to prevent immediate repetition
    last_question_emotion = None
    last_answer_emotion = None

    # Render cold open
    lines.append(
        f"[speaker: {presenter}] [whispering] [annoyed] "
        f"{script.cold_open.complaint_line}"
    )
    lines.append(
        f"[speaker: {presenter}] [shocked] "
        f"{script.cold_open.realization}"
    )
    lines.append(
        f"[speaker: {presenter}] [embarrassed] [sigh] "
        f"{script.cold_open.intro_sentence_1}"
    )
    lines.append(
        f"[speaker: {presenter}] [confident] "
        f"{script.cold_open.intro_sentence_2}"
    )
    lines.append(
        f"[speaker: {presenter}] [intense] "
        f"{script.cold_open.guest_intro}"
    )

    # Render interview segments with programmatic interference injection
    for segment in script.interview_segments:
        # Question from presenter - avoid repeating last emotion
        question_options = [e for e in QUESTION_EMOTIONS if e != last_question_emotion]
        question_emotion = random.choice(question_options)
        last_question_emotion = question_emotion
        question_line = f"[speaker: {presenter}] [{question_emotion}] {segment.question}"
        lines.append(question_line)

        # Answer from source - avoid repeating last emotion
        answer_options = [e for e in ANSWER_EMOTIONS if e != last_answer_emotion]
        answer_emotion = random.choice(answer_options)
        last_answer_emotion = answer_emotion
        answer_line = f"[speaker: {source}] [{answer_emotion}] {segment.answer}"

        # 30% chance to add pause after answer
        if random.random() < 0.3:
            answer_line += f" {random.choice(PAUSES)}"

        lines.append(answer_line)

        # Inject interference acknowledgment if flagged
        if segment.interference_after:
            # Use LLM-generated phrase if available, otherwise fall back to templates
            if segment.interference_phrase:
                interference_phrase = segment.interference_phrase
            else:
                # Fallback to templates if LLM didn't generate a phrase
                if not available_templates:
                    available_templates = list(INTERFERENCE_TEMPLATES)
                interference_phrase = random.choice(available_templates)
                available_templates.remove(interference_phrase)  # Don't reuse

            lines.append(f"[speaker: {presenter}] {interference_phrase}")

            # Track this acknowledgment phrase in metadata
            cleaned_phrase = clean_phrase(interference_phrase)
            metadata["acknowledgment_phrases"].append({
                "line_num": len(lines),  # Line number where phrase appears (1-based)
                "phrase": cleaned_phrase,
                "timestamp": None  # Will be filled in by STT later
            })

    # Render signoff
    lines.append(f"[speaker: {presenter}] [determined] {script.signoff}")

    script_text = "\n".join(lines)

    # Calculate metadata
    metadata["total_lines"] = len(lines)
    metadata["total_words"] = len(script_text.split())

    return script_text, metadata
