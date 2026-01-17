"""Database operations for scheduled shows."""
import logging
import sqlite3
import json
from typing import Optional, List
from datetime import datetime, date
from pathlib import Path
from .show_models import ShowSchedule, GeneratedShow, ShowStatus
from .config import config

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

    def update_show_status(self, show_id: int, status: str) -> None:
        """Update the status of a generated show.

        Args:
            show_id: ID of the generated show to update
            status: New status value (pending, script_complete, ready, script_failed, audio_failed)

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE generated_shows
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, now, show_id))

            conn.commit()
            logger.info(f"Updated show {show_id} status to '{status}'")

        except sqlite3.Error as e:
            logger.error(f"Failed to update show {show_id} status: {e}")
            raise
        finally:
            conn.close()

    def update_show_script(self, show_id: int, script_text: str) -> None:
        """Update the script text of a generated show.

        Args:
            show_id: ID of the generated show to update
            script_text: Script text content

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE generated_shows
                SET script_text = ?, updated_at = ?
                WHERE id = ?
            """, (script_text, now, show_id))

            conn.commit()
            logger.info(f"Updated show {show_id} script text ({len(script_text)} chars)")

        except sqlite3.Error as e:
            logger.error(f"Failed to update show {show_id} script: {e}")
            raise
        finally:
            conn.close()

    def update_show_error(self, show_id: int, error_message: str) -> None:
        """Update the error message of a generated show.

        Args:
            show_id: ID of the generated show to update
            error_message: Error message to store

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE generated_shows
                SET error_message = ?, updated_at = ?
                WHERE id = ?
            """, (error_message, now, show_id))

            conn.commit()
            logger.error(f"Updated show {show_id} error: {error_message}")

        except sqlite3.Error as e:
            logger.error(f"Failed to update show {show_id} error message: {e}")
            raise
        finally:
            conn.close()

    def update_show_asset(self, show_id: int, asset_id: str) -> None:
        """Update the asset ID and mark generation complete for a show.

        Args:
            show_id: ID of the generated show to update
            asset_id: Hex ID from the assets table

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE generated_shows
                SET asset_id = ?, generated_at = ?, updated_at = ?
                WHERE id = ?
            """, (asset_id, now, now, show_id))

            conn.commit()
            logger.info(f"Updated show {show_id} with asset {asset_id}")

        except sqlite3.Error as e:
            logger.error(f"Failed to update show {show_id} asset: {e}")
            raise
        finally:
            conn.close()

    def get_active_schedules(self) -> List[ShowSchedule]:
        """Get all active show schedules.

        Returns:
            List of active ShowSchedule objects

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM show_schedules WHERE active = 1")
            rows = cursor.fetchall()

            schedules = [
                ShowSchedule(
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
                for row in rows
            ]

            logger.info(f"Retrieved {len(schedules)} active schedules")
            return schedules

        except sqlite3.Error as e:
            logger.error(f"Failed to get active schedules: {e}")
            raise
        finally:
            conn.close()

    def get_ready_show(self, schedule_id: int, air_date: date) -> Optional[GeneratedShow]:
        """Get a ready show for a specific schedule and air date.

        Args:
            schedule_id: ID of the show schedule
            air_date: Date to search for

        Returns:
            GeneratedShow instance if found with status='ready', None otherwise

        Raises:
            sqlite3.Error: If database operation fails
        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            air_date_str = air_date.isoformat()
            cursor.execute("""
                SELECT * FROM generated_shows
                WHERE schedule_id = ? AND air_date = ? AND status = ?
            """, (schedule_id, air_date_str, ShowStatus.READY))
            row = cursor.fetchone()

            if not row:
                logger.debug(f"No ready show found for schedule {schedule_id} on {air_date_str}")
                return None

            logger.info(f"Retrieved ready show {row['id']} for schedule {schedule_id} on {air_date_str}")
            return GeneratedShow(
                id=row['id'],
                schedule_id=row['schedule_id'],
                air_date=row['air_date'],
                status=row['status'],
                retry_count=row['retry_count'],
                script_text=row['script_text'],
                asset_id=row['asset_id'],
                generated_at=row['generated_at'],
                error_message=row['error_message'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

        except sqlite3.Error as e:
            logger.error(f"Failed to get ready show for schedule {schedule_id} on {air_date}: {e}")
            raise
        finally:
            conn.close()

    def get_asset_path(self, asset_id: str) -> Path:
        """Get the full filesystem path for an asset.

        Args:
            asset_id: Hex ID from the assets table

        Returns:
            Path object pointing to the asset file

        Raises:
            sqlite3.Error: If database operation fails
            ValueError: If asset_id not found
        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT path FROM assets WHERE id = ?", (asset_id,))
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Asset {asset_id} not found in database")

            path = row['path']
            full_path = Path(path)

            logger.debug(f"Resolved asset {asset_id} to {full_path}")
            return full_path

        except sqlite3.Error as e:
            logger.error(f"Failed to get asset path for {asset_id}: {e}")
            raise
        finally:
            conn.close()
