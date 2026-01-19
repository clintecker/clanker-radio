"""Repair logic for fixing common script violations."""
import logging

from ai_radio.models.script_schema import FieldReportScript


logger: logging.Logger = logging.getLogger(__name__)


def repair_script(script: FieldReportScript) -> FieldReportScript:
    """Apply automatic repairs to common violations.

    Specific repairs applied:
    - Ensures first segment (0) has interference_after=True
    - Adds interference_after=True to fourth segment (3) when script has 7+ segments
    - Adds interference_after=True to seventh segment (6) when script has 8+ segments

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
        logger.info("Repair: Setting interference_after=True on first segment (0)")
        repaired_segments[0].interference_after = True

    # Fix: Add second interference on fourth segment if we have 7+ segments
    # Business rule: 7-segment threshold ensures sufficient content between interruptions
    if len(repaired_segments) >= 7 and not repaired_segments[3].interference_after:
        logger.info("Repair: Setting interference_after=True on fourth segment (3)")
        repaired_segments[3].interference_after = True

    # Fix: Add third interference on seventh segment if we have 8+ segments
    # Spreads three interference points throughout longer interviews
    if len(repaired_segments) >= 8 and not repaired_segments[6].interference_after:
        logger.info("Repair: Setting interference_after=True on seventh segment (6)")
        repaired_segments[6].interference_after = True

    # Return new FieldReportScript with repaired segments
    return FieldReportScript(
        presenter_name=script.presenter_name,
        source_name=script.source_name,
        cold_open=script.cold_open.model_copy(),
        interview_segments=repaired_segments,
        signoff=script.signoff
    )
