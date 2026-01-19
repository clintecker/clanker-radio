"""Repair logic for fixing common script violations."""
import logging

from ai_radio.models.script_schema import FieldReportScript


logger: logging.Logger = logging.getLogger(__name__)


def repair_script(script: FieldReportScript) -> FieldReportScript:
    """Apply automatic repairs to common violations.

    Specific repairs applied:
    - Ensures first segment has interference_after=True
    - Adds interference_after=True to third segment when script has 5+ segments

    Logging behavior:
    - Logs at INFO level when repairs are applied
    - No logs if script already conforms to rules

    This function is safe to call even when no repairs are needed.

    Args:
        script: The script to repair

    Returns:
        Repaired script (new instance, original unchanged)
    """
    # Create mutable copy of segments
    repaired_segments = [s.model_copy() for s in script.interview_segments]

    # Fix: First segment MUST have interference
    if repaired_segments and not repaired_segments[0].interference_after:
        logger.info("Repair: Setting interference_after=True on first segment")
        repaired_segments[0].interference_after = True

    # Fix: Add second interference on third segment if we have 5+ segments
    # Business rule: 5-segment threshold ensures sufficient content between interruptions
    if len(repaired_segments) >= 5 and not repaired_segments[2].interference_after:
        logger.info("Repair: Setting interference_after=True on third segment")
        repaired_segments[2].interference_after = True

    # Return new FieldReportScript with repaired segments
    return FieldReportScript(
        cold_open=script.cold_open.model_copy(),
        interview_segments=repaired_segments,
        signoff=script.signoff
    )
