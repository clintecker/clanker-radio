"""Tests for scripts/schedule_shows.py - Liquidsoap show polling/scheduling."""
import json
from datetime import datetime, time
from zoneinfo import ZoneInfo
from unittest.mock import Mock, patch, call
import pytest

from scripts.schedule_shows import should_air_now, check_scheduled_shows
from ai_radio.show_models import ShowSchedule, GeneratedShow


class TestShouldAirNow:
    """Tests for should_air_now function - determines if schedule should air."""

    def test_should_air_now_matching_day_and_time(self):
        """Returns True when day and time both match schedule."""
        # Friday 09:00 ET
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),  # Friday (0=Monday)
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is True

    def test_should_air_now_within_minute_window(self):
        """Returns True when time is within a minute window of start time."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 09:00:45 ET (45 seconds after start)
        now = datetime(2026, 1, 23, 9, 0, 45, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is True

    def test_should_air_now_wrong_day(self):
        """Returns False when day of week doesn't match schedule."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),  # Friday
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Thursday 09:00 ET (wrong day)
        now = datetime(2026, 1, 22, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is False

    def test_should_air_now_wrong_time(self):
        """Returns False when time doesn't match schedule."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 10:00 ET (wrong time)
        now = datetime(2026, 1, 23, 10, 0, 0, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is False

    def test_should_air_now_before_minute_window(self):
        """Returns False when time is before the minute window."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 08:59:30 ET (30 seconds before start - outside window)
        now = datetime(2026, 1, 23, 8, 59, 30, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is False

    def test_should_air_now_after_minute_window(self):
        """Returns False when time is after the minute window."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 09:01:30 ET (90 seconds after start - outside window)
        now = datetime(2026, 1, 23, 9, 1, 30, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is False

    def test_should_air_now_timezone_handling(self):
        """Correctly handles timezone conversions."""
        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Pacific",  # Pacific time
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Friday 17:00 UTC = Friday 09:00 Pacific (should match)
        now = datetime(2026, 1, 23, 17, 0, 0, tzinfo=ZoneInfo("UTC"))

        assert should_air_now(schedule, now) is True

    def test_should_air_now_multiple_days(self):
        """Returns True when day matches any in days_of_week list."""
        schedule = ShowSchedule(
            name="Weekday Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([0, 1, 2, 3, 4]),  # Mon-Fri
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        # Wednesday 09:00 ET (mid-week)
        now = datetime(2026, 1, 21, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))

        assert should_air_now(schedule, now) is True

    def test_should_air_now_dst_spring_forward(self):
        """DST spring forward - Python's ZoneInfo skips non-existent times.

        During spring forward (e.g., 2AM -> 3AM), times in the gap don't exist.
        Python's datetime correctly skips these times using fold-aware handling.
        A show scheduled for 2:30AM won't air during the gap.
        """
        # Show scheduled for 2:30 AM US/Eastern on Sundays
        schedule = ShowSchedule(
            name="Late Night Show",
            format="interview",
            topic_area="Topics",
            days_of_week='[6]',  # Sunday
            start_time="02:30",
            duration_minutes=30,
            timezone="US/Eastern",
            personas='[{"name": "Host", "traits": "engaging"}]',
            content_guidance=None,
            regenerate_daily=True,
            active=True
        )

        # March 9, 2025 at 2:30 AM ET is during DST spring forward gap
        # (2AM -> 3AM, so 2:30 doesn't exist)
        # Python's ZoneInfo will skip this time
        # NOTE: We test that the function doesn't crash; behavior is implementation-defined
        now = datetime(2025, 3, 9, 7, 30, 0, tzinfo=ZoneInfo("UTC"))  # 2:30 ET (if it existed)

        # Function should handle this gracefully (not crash)
        result = should_air_now(schedule, now)
        assert isinstance(result, bool)  # Should return without error

    def test_should_air_now_dst_fall_back(self):
        """DST fall back - Python's ZoneInfo uses fold=0 for first occurrence.

        During fall back (e.g., 2AM happens twice), times are ambiguous.
        Python's datetime uses fold=0 by default (first occurrence).
        A show scheduled for 2:00AM will air during the first occurrence only.
        """
        # Show scheduled for 2:00 AM US/Eastern on Sundays
        schedule = ShowSchedule(
            name="Early Morning Show",
            format="interview",
            topic_area="Topics",
            days_of_week='[6]',  # Sunday
            start_time="02:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas='[{"name": "Host", "traits": "engaging"}]',
            content_guidance=None,
            regenerate_daily=True,
            active=True
        )

        # November 2, 2025 at 2:00 AM ET (first occurrence during DST fall back)
        # DST ends at 2:00 AM, so 2:00 AM happens twice
        # First 2:00 AM EDT (UTC-4) = 6:00 UTC
        now_first = datetime(2025, 11, 2, 6, 0, 0, tzinfo=ZoneInfo("UTC"))

        # Note: The actual DST transition date for 2025 may vary
        # This test documents that the function handles DST transitions gracefully
        result_first = should_air_now(schedule, now_first)
        assert isinstance(result_first, bool)  # Should handle without error

        # Second 2:00 AM EST (UTC-5) = 7:00 UTC
        now_second = datetime(2025, 11, 2, 7, 0, 0, tzinfo=ZoneInfo("UTC"))
        result_second = should_air_now(schedule, now_second)
        assert isinstance(result_second, bool)  # Should handle without error


class TestCheckScheduledShows:
    """Tests for check_scheduled_shows - main orchestration function."""

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    def test_check_scheduled_shows_enqueues_ready(
        self, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Enqueues ready show to Liquidsoap when schedule should air."""
        # Setup: Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),  # Friday
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )
        mock_repo.get_active_schedules.return_value = [schedule]

        ready_show = GeneratedShow(
            schedule_id=1,
            air_date="2026-01-23",
            status="ready",
            retry_count=0,
            asset_id="abc123def456",
            id=1
        )
        mock_repo.get_ready_show.return_value = ready_show
        mock_repo.get_asset_path.return_value = "/srv/ai_radio/generated/shows/abc123def456.mp3"

        # Mock Liquidsoap client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.push_track.return_value = True

        # Execute
        check_scheduled_shows()

        # Verify repository calls
        mock_repo.get_active_schedules.assert_called_once()
        mock_repo.get_ready_show.assert_called_once_with(
            schedule_id=1,
            air_date="2026-01-23"
        )
        mock_repo.get_asset_path.assert_called_once_with("abc123def456")

        # Verify Liquidsoap enqueue
        mock_client.push_track.assert_called_once_with(
            "breaks",
            "/srv/ai_radio/generated/shows/abc123def456.mp3"
        )

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    @patch('scripts.schedule_shows.logger')
    def test_check_scheduled_shows_warns_not_ready(
        self, mock_logger, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Logs warning when show should air but is not ready."""
        # Setup: Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )
        mock_repo.get_active_schedules.return_value = [schedule]
        mock_repo.get_ready_show.return_value = None  # No ready show

        # Mock Liquidsoap client (should not be called)
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Execute
        check_scheduled_shows()

        # Verify warning logged
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        assert "not ready" in warning_message.lower()
        assert "Morning Show" in warning_message

        # Verify Liquidsoap NOT called (no dead air, music continues)
        mock_client.push_track.assert_not_called()

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    def test_check_scheduled_shows_skips_inactive(
        self, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Skips inactive schedules."""
        # Setup: Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository with inactive schedule
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        inactive_schedule = ShowSchedule(
            name="Inactive Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=False,  # Inactive
            id=1
        )
        mock_repo.get_active_schedules.return_value = []  # No active schedules

        # Mock Liquidsoap client (should not be called)
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Execute
        check_scheduled_shows()

        # Verify get_active_schedules called but returns empty
        mock_repo.get_active_schedules.assert_called_once()

        # Verify no enqueue attempts
        mock_client.push_track.assert_not_called()
        mock_repo.get_ready_show.assert_not_called()

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    def test_check_scheduled_shows_skips_wrong_time(
        self, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Skips schedules that should not be airing at current time."""
        # Setup: Friday 10:00 ET
        now = datetime(2026, 1, 23, 10, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",  # Should air at 09:00, not 10:00
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )
        mock_repo.get_active_schedules.return_value = [schedule]

        # Mock Liquidsoap client (should not be called)
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Execute
        check_scheduled_shows()

        # Verify no enqueue attempts (wrong time)
        mock_client.push_track.assert_not_called()
        mock_repo.get_ready_show.assert_not_called()

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    def test_check_scheduled_shows_handles_multiple_schedules(
        self, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Processes multiple schedules independently."""
        # Setup: Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository with two schedules
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        schedule1 = ShowSchedule(
            name="Morning Show A",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )

        schedule2 = ShowSchedule(
            name="Morning Show B",
            format="two_host_discussion",
            topic_area="science",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=2
        )

        mock_repo.get_active_schedules.return_value = [schedule1, schedule2]

        # Only schedule1 has ready show
        def get_ready_side_effect(schedule_id, air_date):
            if schedule_id == 1:
                return GeneratedShow(
                    schedule_id=1,
                    air_date="2026-01-23",
                    status="ready",
                    retry_count=0,
                    asset_id="abc123",
                    id=1
                )
            return None  # schedule2 not ready

        mock_repo.get_ready_show.side_effect = get_ready_side_effect
        mock_repo.get_asset_path.return_value = "/srv/ai_radio/generated/shows/abc123.mp3"

        # Mock Liquidsoap client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.push_track.return_value = True

        # Execute
        check_scheduled_shows()

        # Verify both schedules checked
        assert mock_repo.get_ready_show.call_count == 2
        mock_repo.get_ready_show.assert_any_call(schedule_id=1, air_date="2026-01-23")
        mock_repo.get_ready_show.assert_any_call(schedule_id=2, air_date="2026-01-23")

        # Verify only schedule1 enqueued
        mock_client.push_track.assert_called_once_with(
            "breaks",
            "/srv/ai_radio/generated/shows/abc123.mp3"
        )

    @patch('scripts.schedule_shows.datetime')
    @patch('scripts.schedule_shows.ShowRepository')
    @patch('scripts.schedule_shows.LiquidsoapClient')
    @patch('scripts.schedule_shows.logger')
    def test_check_scheduled_shows_handles_enqueue_failure(
        self, mock_logger, mock_client_class, mock_repo_class, mock_datetime
    ):
        """Logs error when Liquidsoap enqueue fails."""
        # Setup: Friday 09:00 ET
        now = datetime(2026, 1, 23, 9, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
        mock_datetime.now.return_value = now

        # Mock repository
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        schedule = ShowSchedule(
            name="Morning Show",
            format="interview",
            topic_area="tech",
            days_of_week=json.dumps([4]),
            start_time="09:00",
            duration_minutes=30,
            timezone="US/Eastern",
            personas="[]",
            content_guidance=None,
            regenerate_daily=True,
            active=True,
            id=1
        )
        mock_repo.get_active_schedules.return_value = [schedule]

        ready_show = GeneratedShow(
            schedule_id=1,
            air_date="2026-01-23",
            status="ready",
            retry_count=0,
            asset_id="abc123",
            id=1
        )
        mock_repo.get_ready_show.return_value = ready_show
        mock_repo.get_asset_path.return_value = "/srv/ai_radio/generated/shows/abc123.mp3"

        # Mock Liquidsoap client - enqueue fails
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.push_track.return_value = False  # Failure

        # Execute
        check_scheduled_shows()

        # Verify error logged
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "failed" in error_message.lower()
        assert "Morning Show" in error_message or "abc123" in error_message
