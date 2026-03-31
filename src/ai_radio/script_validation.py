"""Validation logic for field report scripts."""
from dataclasses import dataclass
from ai_radio.models.script_schema import FieldReportScript


@dataclass
class ValidationIssue:
    """A validation issue found in the script."""
    field: str
    message: str
    severity: str = "error"  # error, warning


def validate_script(script: FieldReportScript) -> list[ValidationIssue]:
    """Validate script structure and constraints.

    Args:
        script: The field report script to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    # Validate cold open word counts
    complaint_words = len(script.cold_open.complaint_line.split())
    if complaint_words > 25:
        issues.append(ValidationIssue(
            field="cold_open.complaint_line",
            message=f"Complaint line too long: {complaint_words} words (max 25 words)"
        ))

    intro1_words = len(script.cold_open.intro_sentence_1.split())
    if intro1_words > 30:
        issues.append(ValidationIssue(
            field="cold_open.intro_sentence_1",
            message=f"Intro sentence 1 too long: {intro1_words} words (max 30 words)"
        ))

    intro2_words = len(script.cold_open.intro_sentence_2.split())
    if intro2_words > 35:
        issues.append(ValidationIssue(
            field="cold_open.intro_sentence_2",
            message=f"Intro sentence 2 too long: {intro2_words} words (max 35 words)"
        ))

    guest_intro_words = len(script.cold_open.guest_intro.split())
    if guest_intro_words > 35:
        issues.append(ValidationIssue(
            field="cold_open.guest_intro",
            message=f"Guest intro too long: {guest_intro_words} words (max 35 words)"
        ))

    # Validate interview segments
    for i, segment in enumerate(script.interview_segments):
        question_words = len(segment.question.split())
        if question_words > 40:
            issues.append(ValidationIssue(
                field=f"interview_segments[{i}].question",
                message=f"Question too long: {question_words} words (max 40 words)"
            ))

        answer_words = len(segment.answer.split())
        if answer_words > 60:
            issues.append(ValidationIssue(
                field=f"interview_segments[{i}].answer",
                message=f"Answer too long: {answer_words} words (max 60 words)"
            ))

    # Validate interference placement
    if script.interview_segments:
        if not script.interview_segments[0].interference_after:
            issues.append(ValidationIssue(
                field="interview_segments[0].interference_after",
                message="First segment must have interference_after=True"
            ))

    # Validate total word count
    total_words = (
        len(script.cold_open.complaint_line.split()) +
        len(script.cold_open.realization.split()) +
        len(script.cold_open.intro_sentence_1.split()) +
        len(script.cold_open.intro_sentence_2.split()) +
        len(script.cold_open.guest_intro.split()) +
        sum(len(s.question.split()) + len(s.answer.split()) for s in script.interview_segments) +
        len(script.signoff.split())
    )

    if total_words > 1000:
        issues.append(ValidationIssue(
            field="total_word_count",
            message=f"Script too long: {total_words} words (max 1000 words)",
            severity="warning"
        ))

    return issues
