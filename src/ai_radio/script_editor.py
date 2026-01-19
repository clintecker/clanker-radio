"""Script editor for word count enforcement via compression."""
import logging

import google.genai as genai

from ai_radio.config import config
from ai_radio.models.script_schema import FieldReportScript, InterviewSegment


logger = logging.getLogger(__name__)

# Model configuration constants
EDITOR_MODEL = "gemini-2.0-flash-exp"
# Temperature 0.0 ensures deterministic, consistent compression results
EDITOR_TEMPERATURE = 0.0


def compress_script_to_budget(
    script: FieldReportScript,
    target_words: int
) -> FieldReportScript:
    """Compress script to fit word budget by shortening answers.

    Uses LLM editor to make surgical edits only to answers,
    preserving cold open, questions, and structure.

    Args:
        script: The script to compress
        target_words: Target total word count

    Returns:
        Compressed script at or near target
    """
    # Calculate current word count
    current_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split()) +
        sum(
            len(s.question.split()) + len(s.answer.split())
            for s in script.interview_segments
        ) +
        len(script.signoff.split())
    )

    if current_words <= target_words:
        logger.info(f"Script already at budget: {current_words} <= {target_words}")
        return script

    # Calculate how much to reduce
    words_to_cut = current_words - target_words
    reduction_pct = (words_to_cut / current_words) * 100

    logger.info(
        f"Compressing script: {current_words} → {target_words} words "
        f"({reduction_pct:.1f}% reduction)"
    )

    # Build prompt for editor
    answers_text = "\n\n".join([
        f"ANSWER {i+1}:\n{seg.answer}"
        for i, seg in enumerate(script.interview_segments)
    ])

    prompt = f"""Edit these interview answers to reduce total length by {reduction_pct:.0f}%.

TARGET: Cut approximately {words_to_cut} words total

RULES:
- Make answers more concise while preserving key information
- Maintain natural speaking tone
- Keep answers substantial (not too terse)
- Distribute cuts across all answers proportionally

ANSWERS TO COMPRESS:

{answers_text}

OUTPUT: Return ONLY the compressed answers in the same format:

ANSWER 1:
[compressed answer 1]

ANSWER 2:
[compressed answer 2]

etc."""

    client = genai.Client(api_key=config.api_keys.gemini_api_key.get_secret_value())

    try:
        response = client.models.generate_content(
            model=EDITOR_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(temperature=EDITOR_TEMPERATURE)
        )
    except Exception as e:
        logger.error(f"LLM API call failed during script compression: {e}")
        logger.warning("Returning original script uncompressed")
        return script

    # Parse compressed answers
    compressed_answers = []
    current_answer = []

    for line in response.text.split('\n'):
        if line.strip().startswith("ANSWER"):
            if current_answer:
                compressed_answers.append('\n'.join(current_answer).strip())
                current_answer = []
        else:
            if line.strip():
                current_answer.append(line)

    if current_answer:
        compressed_answers.append('\n'.join(current_answer).strip())

    # Validate response - ensure we got the right number of answers
    expected_count = len(script.interview_segments)
    actual_count = len(compressed_answers)

    if actual_count != expected_count:
        logger.warning(
            f"LLM returned {actual_count} answers but expected {expected_count}. "
            f"Using available answers and preserving originals for missing."
        )

    # Build new segments with compressed answers
    new_segments = []
    for i, segment in enumerate(script.interview_segments):
        if i < len(compressed_answers):
            new_segments.append(
                InterviewSegment(
                    question=segment.question,
                    answer=compressed_answers[i],
                    interference_after=segment.interference_after
                )
            )
        else:
            new_segments.append(segment)

    # Return new script with compressed segments
    return FieldReportScript(
        cold_open=script.cold_open.model_copy(),
        interview_segments=new_segments,
        signoff=script.signoff
    )
