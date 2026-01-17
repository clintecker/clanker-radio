"""Data models for scheduled shows."""
from dataclasses import dataclass
from typing import Optional


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
