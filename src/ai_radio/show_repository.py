"""Database operations for scheduled shows."""
import logging
import sqlite3
import json
from typing import Optional, List
from datetime import datetime
from .show_models import ShowSchedule, GeneratedShow

logger = logging.getLogger(__name__)


class ShowRepository:
    """Repository for show schedule and generated show operations."""

    def __init__(self, db_path: str):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection.

        Returns:
            SQLite database connection
        """
        return sqlite3.connect(self.db_path)

    def create_schedule(self, schedule: ShowSchedule) -> int:
        """Create a new show schedule.

        Args:
            schedule: ShowSchedule model instance to create

        Returns:
            ID of created schedule

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
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

            logger.info(f"Created schedule {schedule_id}: {schedule.name}")
            return schedule_id

        except sqlite3.Error as e:
            logger.error(f"Failed to create schedule: {e}")
            raise
        finally:
            conn.close()

    def get_schedule(self, schedule_id: int) -> Optional[ShowSchedule]:
        """Get a schedule by ID.

        Args:
            schedule_id: ID of the schedule to retrieve

        Returns:
            ShowSchedule instance if found, None otherwise

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM show_schedules WHERE id = ?", (schedule_id,))
            row = cursor.fetchone()

            if not row:
                logger.debug(f"Schedule {schedule_id} not found")
                return None

            logger.debug(f"Retrieved schedule {schedule_id}: {row['name']}")
            return ShowSchedule(
                id=row['id'],
                name=row['name'],
                format=row['format'],
                topic_area=row['topic_area'],
                days_of_week=row['days_of_week'],
                start_time=row['start_time'],
                duration_minutes=row['duration_minutes'],
                timezone=row['timezone'],
                personas=row['personas'],
                content_guidance=row['content_guidance'],
                regenerate_daily=bool(row['regenerate_daily']),
                active=bool(row['active']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to get schedule {schedule_id}: {e}")
            raise
        finally:
            conn.close()
