"""Tests for scripts/generate_shows.py orchestration."""
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_radio.show_models import GeneratedShow, ShowSchedule, ShowStatus
from ai_radio.show_repository import ShowRepository
from scripts.generate_shows import generate_one, needs_generation, run


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    migration = Path(__file__).parent.parent / "migrations/008_create_show_tables.sql"
    conn.executescript(migration.read_text())
    conn.close()
    r = ShowRepository(str(db_path))
    r.create_schedule(ShowSchedule(
        name="The AI Report", format="interview", topic_area="AI",
        days_of_week=json.dumps([0, 1, 2, 3, 4, 5, 6]), start_time="15:30",
        duration_minutes=8, timezone="US/Eastern", personas="[]",
        content_guidance=None, regenerate_daily=True, active=True,
    ))
    return r


def show(status, retry_count=0):
    return GeneratedShow(id=1, schedule_id=1, air_date="2026-09-22", status=status,
                         retry_count=retry_count, error_message="boom")


class TestNeedsGeneration:
    def test_ready_is_done(self):
        assert needs_generation(show(ShowStatus.READY), 3) is False

    def test_pending_and_script_complete_need_work(self):
        assert needs_generation(show(ShowStatus.PENDING), 3)
        assert needs_generation(show(ShowStatus.SCRIPT_COMPLETE), 3)

    def test_failed_retries_until_limit(self):
        assert needs_generation(show(ShowStatus.AUDIO_FAILED, retry_count=2), 3)
        assert needs_generation(show(ShowStatus.AUDIO_FAILED, retry_count=3), 3) is False
        assert needs_generation(show(ShowStatus.SCRIPT_FAILED, retry_count=3), 3) is False


class TestGetOrCreateShow:
    def test_creates_pending_row_once(self, repo):
        a = repo.get_or_create_show(1, date(2026, 9, 22))
        b = repo.get_or_create_show(1, date(2026, 9, 22))
        assert a.id == b.id
        assert a.status == ShowStatus.PENDING
        assert a.air_date == "2026-09-22"

    def test_increment_retry_count(self, repo):
        s = repo.get_or_create_show(1, date(2026, 9, 22))
        assert repo.increment_retry_count(s.id) == 1
        assert repo.increment_retry_count(s.id) == 2


class TestGenerateOne:
    def test_successful_generation_returns_ready(self, repo):
        schedule = repo.get_active_schedules()[0]

        def fake_generate(sched, shw):
            repo.update_show_asset(shw.id, "abc")
            repo.update_show_status(shw.id, ShowStatus.READY)

        generator = Mock(generate=Mock(side_effect=fake_generate))
        assert generate_one(repo, generator, schedule, date(2026, 9, 22), 3) == ShowStatus.READY
        assert repo.get_ready_show(schedule.id, date(2026, 9, 22)).asset_id == "abc"

    def test_failed_generation_bumps_retry_count(self, repo):
        schedule = repo.get_active_schedules()[0]

        def fake_generate(sched, shw):
            repo.update_show_status(shw.id, ShowStatus.AUDIO_FAILED)
            repo.update_show_error(shw.id, "tts exploded")

        generator = Mock(generate=Mock(side_effect=fake_generate))
        assert generate_one(repo, generator, schedule, date(2026, 9, 22), 3) == ShowStatus.AUDIO_FAILED
        assert repo.get_or_create_show(1, date(2026, 9, 22)).retry_count == 1

    def test_audio_failed_retry_resumes_from_script(self, repo):
        schedule = repo.get_active_schedules()[0]
        s = repo.get_or_create_show(1, date(2026, 9, 22))
        repo.update_show_script(s.id, "the script")
        repo.update_show_status(s.id, ShowStatus.AUDIO_FAILED)

        seen = {}
        def fake_generate(sched, shw):
            seen["status"] = shw.status
            repo.update_show_status(shw.id, ShowStatus.READY)

        generate_one(repo, Mock(generate=Mock(side_effect=fake_generate)), schedule, date(2026, 9, 22), 3)
        assert seen["status"] == ShowStatus.SCRIPT_COMPLETE

    def test_ready_show_is_skipped(self, repo):
        schedule = repo.get_active_schedules()[0]
        s = repo.get_or_create_show(1, date(2026, 9, 22))
        repo.update_show_status(s.id, ShowStatus.READY)
        generator = Mock()
        assert generate_one(repo, generator, schedule, date(2026, 9, 22), 3) is None
        generator.generate.assert_not_called()


class TestRun:
    @patch("scripts.generate_shows.ShowGenerator")
    @patch("scripts.generate_shows.ShowRepository")
    @patch("scripts.generate_shows.config")
    def test_run_skips_schedules_outside_lead_window(self, mock_config, mock_repo_cls, mock_gen_cls, repo):
        mock_config.paths.db_path = "unused"
        mock_config.show_generation_lead_hours = 6.0
        mock_config.show_generation_max_retries = 3
        mock_repo_cls.return_value = repo
        # 08:00 Eastern = 12:00 UTC, 7.5h before the 15:30 airing
        now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
        assert run(now=now) == 0
        mock_gen_cls.return_value.generate.assert_not_called()

    @patch("scripts.generate_shows.ShowGenerator")
    @patch("scripts.generate_shows.ShowRepository")
    @patch("scripts.generate_shows.config")
    def test_run_generates_when_due(self, mock_config, mock_repo_cls, mock_gen_cls, repo):
        mock_config.paths.db_path = "unused"
        mock_config.show_generation_lead_hours = 6.0
        mock_config.show_generation_max_retries = 3
        mock_repo_cls.return_value = repo

        def fake_generate(sched, shw):
            repo.update_show_status(shw.id, ShowStatus.READY)
        mock_gen_cls.return_value.generate.side_effect = fake_generate

        now = datetime(2026, 9, 22, 18, 0, tzinfo=timezone.utc)  # 14:00 Eastern
        assert run(now=now) == 1
        assert repo.get_ready_show(1, date(2026, 9, 22)) is not None
