"""Database operations for scheduled shows."""
import sqlite3
import json
from typing import Optional, List
from datetime import datetime
from .show_models import ShowSchedule, GeneratedShow


class ShowRepository:
    """Repository for show schedule and generated show operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def create_schedule(self, schedule: ShowSchedule) -> int:
        """Create a new show schedule.

        Returns:
            ID of created schedule
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO show_schedules (
                name, format, topic_area, days_of_week, start_time,
                duration_minutes, timezone, personas, content_guidance,
                regenerate_daily, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule.name,
            schedule.format,
            schedule.topic_area,
            schedule.days_of_week,
            schedule.start_time,
            schedule.duration_minutes,
            schedule.timezone,
            schedule.personas,
            schedule.content_guidance,
            schedule.regenerate_daily,
            schedule.active
        ))

        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return schedule_id

    def get_schedule(self, schedule_id: int) -> Optional[ShowSchedule]:
        """Get a schedule by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM show_schedules WHERE id = ?", (schedule_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ShowSchedule(
            id=row[0],
            name=row[1],
            format=row[2],
            topic_area=row[3],
            days_of_week=row[4],
            start_time=row[5],
            duration_minutes=row[6],
            timezone=row[7],
            personas=row[8],
            content_guidance=row[9],
            regenerate_daily=bool(row[10]),
            active=bool(row[11]),
            created_at=row[12],
            updated_at=row[13]
        )
