"""Render structured scripts to final text format with programmatic interference."""
import random

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


def render_script(
    script: FieldReportScript,
    presenter: str,
    source: str
) -> str:
    """Render structured script to final text format with speaker tags.

    Programmatically injects interference acknowledgments from templates
    rather than relying on model generation.

    Args:
        script: The structured script to render
        presenter: Name of the presenter/reporter
        source: Name of the interview source

    Returns:
        Formatted script text with speaker tags and interference
    """
    lines = []

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

    # Render interview segments with programmatic interference injection
    for segment in script.interview_segments:
        # Question from presenter
        lines.append(f"[speaker: {presenter}] {segment.question}")

        # Answer from source
        lines.append(f"[speaker: {source}] [earnest] {segment.answer}")

        # Inject interference acknowledgment if flagged
        # Intentional randomness: selects from template pool for natural variety
        if segment.interference_after:
            interference_phrase = random.choice(INTERFERENCE_TEMPLATES)
            lines.append(f"[speaker: {presenter}] {interference_phrase}")

    # Render signoff
    lines.append(f"[speaker: {presenter}] [determined] {script.signoff}")

    return "\n".join(lines)
