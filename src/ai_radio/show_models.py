"""Data models for scheduled shows."""
from dataclasses import dataclass
from typing import Optional


# Show generation status constants
class ShowStatus:
    """Status values for GeneratedShow state machine."""
    PENDING = "pending"
    SCRIPT_COMPLETE = "script_complete"
    READY = "ready"
    SCRIPT_FAILED = "script_failed"
    AUDIO_FAILED = "audio_failed"


# Show format constants
class ShowFormat:
    """Supported show formats."""
    INTERVIEW = "interview"
    TWO_HOST_DISCUSSION = "two_host_discussion"


# Liquidsoap queue constants
class LiquidsoapQueue:
    """Liquidsoap queue names."""
    BREAKS = "breaks"


@dataclass
class ShowSchedule:
    """Represents a scheduled AI-generated radio show.

    Maps to show_schedules table in database.
    """
    name: str
    format: str  # 'interview' or 'two_host_discussion'
    topic_area: str

    # Timing (stored as JSON strings in DB)
    days_of_week: str  # JSON: [1,2,3,4,5]
    start_time: str  # "09:00"
    duration_minutes: int
    timezone: str

    # Show configuration (stored as JSON strings in DB)
    personas: str  # JSON: [{"name": "...", "traits": "..."}]
    content_guidance: Optional[str]
    regenerate_daily: bool

    # State
    active: bool

    # Auto-populated by DB (optional for creation)
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class GeneratedShow:
    """Represents a generated instance of a scheduled show.

    Maps to generated_shows table. Tracks the state machine:
    pending → script_complete → ready (or → script_failed / audio_failed)
    """
    schedule_id: int
    air_date: str  # "2026-01-18"
    status: str    # 'pending', 'script_complete', 'ready', 'script_failed', 'audio_failed'
    retry_count: int

    # Artifacts (populated during generation)
    script_text: Optional[str] = None
    asset_id: Optional[str] = None  # Hex ID from assets table

    # Metadata
    generated_at: Optional[str] = None
    error_message: Optional[str] = None

    # Auto-populated by DB (optional for creation)
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
