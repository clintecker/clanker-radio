"""Tests for show database operations."""
import json
import sqlite3
import pytest
from pathlib import Path
from ai_radio.show_repository import ShowRepository
from ai_radio.show_models import ShowSchedule


@pytest.fixture
def test_db(tmp_path):
    """Create test database with migrations."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    # Apply migration
    migration_sql = Path("db/migrations/005_add_scheduled_shows.sql").read_text()
    conn.executescript(migration_sql)
    conn.close()

    return str(db_path)


def test_create_schedule(test_db):
    """Test creating and retrieving a schedule."""
    repo = ShowRepository(test_db)

    schedule = ShowSchedule(
        name="Tech Talk",
        format="interview",
        topic_area="AI developments",
        days_of_week=json.dumps([1, 3, 5]),
        start_time="14:00",
        duration_minutes=8,
        timezone="America/Chicago",
        personas=json.dumps([
            {"name": "Host", "traits": "curious"},
            {"name": "Expert", "traits": "knowledgeable"}
        ]),
        content_guidance="Latest AI news",
        regenerate_daily=True,
        active=True
    )

    saved_id = repo.create_schedule(schedule)
    assert saved_id is not None

    retrieved = repo.get_schedule(saved_id)
    assert retrieved.name == "Tech Talk"
    assert retrieved.format == "interview"
