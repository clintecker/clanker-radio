# Scheduled AI-Generated Radio Shows - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement scheduled AI radio show generation with natural language parsing, overnight batch generation, and automated broadcasting.

**Architecture:** Vertical slice TDD approach. Build complete features end-to-end in small increments. Database → Models → Parser → Generator → Service.

**Tech Stack:** SQLite, SQLAlchemy, Gemini API (script + TTS), existing break_generator pipeline patterns

---

## Implementation Strategy

**Approach:** Feature Slices (Vertical Slices) - Build one complete piece of end-to-end functionality at a time.

**Task Groups:**
1. **Foundation** - Database schema + models
2. **Schedule Creation** - Parser + conflict detection
3. **Generation Pipeline** - Research → Script → TTS
4. **Service Layer** - Overnight batch generator
5. **Broadcasting** - Liquidsoap integration
6. **Robustness** - Retries, monitoring, validation

---

## Group 1: Foundation - Database & Models

### Task 1.1: Create SQL Migration

**Files:**
- Create: `db/migrations/005_add_scheduled_shows.sql`

**Step 1: Write the migration**

Create `db/migrations/005_add_scheduled_shows.sql`:

```sql
-- Migration: Add scheduled shows tables
-- Creates show_schedules and generated_shows with state machine

BEGIN TRANSACTION;

CREATE TABLE show_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('interview', 'two_host_discussion')),
    topic_area TEXT NOT NULL,

    -- Timing
    days_of_week TEXT NOT NULL,            -- JSON: [1,2,3,4,5]
    start_time TEXT NOT NULL,              -- "09:00"
    duration_minutes INTEGER DEFAULT 8,
    timezone TEXT DEFAULT 'America/New_York',

    -- Show configuration
    personas TEXT NOT NULL,                 -- JSON: [{"name": "Marco", "traits": "..."}]
    content_guidance TEXT,
    regenerate_daily BOOLEAN DEFAULT 1,

    -- State
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schedules_active ON show_schedules(active);

CREATE TABLE generated_shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,
    air_date DATE NOT NULL,

    -- State machine: pending → script_complete → ready (or → script_failed / audio_failed)
    status TEXT NOT NULL CHECK(status IN ('pending', 'script_complete', 'ready', 'script_failed', 'audio_failed')),
    retry_count INTEGER DEFAULT 0,

    -- Artifacts
    script_text TEXT,
    asset_id TEXT,  -- Hex ID from assets table

    -- Metadata
    generated_at TIMESTAMP,
    error_message TEXT,

    UNIQUE(schedule_id, air_date),
    FOREIGN KEY(schedule_id) REFERENCES show_schedules(id) ON DELETE CASCADE
);

CREATE INDEX idx_generated_shows_status_air_date ON generated_shows(status, air_date);

COMMIT;
```

**Step 2: Apply the migration**

Run: `sqlite3 /srv/ai_radio/db/radio.sqlite3 < db/migrations/005_add_scheduled_shows.sql`
Expected: Migration succeeds

**Step 3: Verify schema**

Run: `sqlite3 /srv/ai_radio/db/radio.sqlite3 ".schema show_schedules"`
Expected: Shows CREATE TABLE statement

**Step 4: Commit**

```bash
git add db/migrations/005_add_scheduled_shows.sql
git commit -m "feat: add show_schedules and generated_shows tables"
```

---

### Task 1.2: Write failing test for ShowSchedule model

**Files:**
- Create: `tests/test_show_models.py`

**Step 1: Write the failing test**

Create `tests/test_show_models.py`:

```python
"""Tests for scheduled show models."""
import json
import pytest
from datetime import datetime
from ai_radio.show_models import ShowSchedule


def test_create_show_schedule(tmp_path):
    """Test creating a ShowSchedule with all required fields."""
    schedule = ShowSchedule(
        name="Crypto Morning Show",
        format="two_host_discussion",
        topic_area="Bitcoin and DeFi news",
        days_of_week=json.dumps([1, 2, 3, 4, 5]),  # M-F
        start_time="09:00",
        duration_minutes=8,
        timezone="America/New_York",
        personas=json.dumps([
            {"name": "Marco", "traits": "skeptical, data-driven"},
            {"name": "Chloe", "traits": "optimistic, long-term"}
        ]),
        content_guidance="Latest crypto news and market analysis",
        regenerate_daily=True,
        active=True
    )

    assert schedule.name == "Crypto Morning Show"
    assert schedule.format == "two_host_discussion"
    assert json.loads(schedule.days_of_week) == [1, 2, 3, 4, 5]
    assert schedule.active is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_show_models.py::test_create_show_schedule -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.show_models'"

---

### Task 1.3: Create minimal ShowSchedule model

**Files:**
- Create: `src/ai_radio/show_models.py`

**Step 1: Write minimal implementation**

Create `src/ai_radio/show_models.py`:

```python
"""Data models for scheduled radio shows."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ShowSchedule:
    """A scheduled radio show configuration."""

    # Identity
    name: str
    format: str  # 'interview' or 'two_host_discussion'
    topic_area: str

    # Timing
    days_of_week: str  # JSON array: [1,2,3,4,5]
    start_time: str    # "09:00"
    duration_minutes: int
    timezone: str

    # Configuration
    personas: str  # JSON array of {name, traits}
    content_guidance: Optional[str]
    regenerate_daily: bool

    # State
    active: bool
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_show_models.py::test_create_show_schedule -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ai_radio/show_models.py tests/test_show_models.py
git commit -m "feat: add ShowSchedule dataclass model"
```

---

### Task 1.4: Write failing test for GeneratedShow model

**Files:**
- Modify: `tests/test_show_models.py`

**Step 1: Add failing test**

Add to `tests/test_show_models.py`:

```python
from ai_radio.show_models import GeneratedShow


def test_create_generated_show():
    """Test creating a GeneratedShow with state machine."""
    show = GeneratedShow(
        schedule_id=1,
        air_date="2026-01-18",
        status="pending",
        retry_count=0
    )

    assert show.schedule_id == 1
    assert show.air_date == "2026-01-18"
    assert show.status == "pending"
    assert show.retry_count == 0
    assert show.script_text is None
    assert show.asset_id is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_show_models.py::test_create_generated_show -v`
Expected: FAIL with "cannot import name 'GeneratedShow'"

---

### Task 1.5: Create minimal GeneratedShow model

**Files:**
- Modify: `src/ai_radio/show_models.py`

**Step 1: Add to show_models.py**

```python
@dataclass
class GeneratedShow:
    """A generated instance of a scheduled show."""

    schedule_id: int
    air_date: str  # "2026-01-18"
    status: str    # 'pending', 'script_complete', 'ready', 'script_failed', 'audio_failed'
    retry_count: int

    # Artifacts
    script_text: Optional[str] = None
    asset_id: Optional[str] = None

    # Metadata
    error_message: Optional[str] = None
    generated_at: Optional[datetime] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Step 2: Run test**

Run: `pytest tests/test_show_models.py::test_create_generated_show -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ai_radio/show_models.py tests/test_show_models.py
git commit -m "feat: add GeneratedShow dataclass model"
```

---

## Group 2: Database Layer - CRUD Operations

### Task 2.1: Write failing test for schedule creation

**Files:**
- Create: `tests/test_show_repository.py`

**Step 1: Write test**

Create `tests/test_show_repository.py`:

```python
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
```

**Step 2: Run test**

Run: `pytest tests/test_show_repository.py::test_create_schedule -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.show_repository'"

---

### Task 2.2: Implement ShowRepository

**Files:**
- Create: `src/ai_radio/show_repository.py`

**Step 1: Write implementation**

Create `src/ai_radio/show_repository.py`:

```python
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
```

**Step 2: Run test**

Run: `pytest tests/test_show_repository.py::test_create_schedule -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ai_radio/show_repository.py tests/test_show_repository.py
git commit -m "feat: implement ShowRepository with create/get"
```

---

## Group 3: Schedule Parser - Natural Language to Structured Format

### Task 3.1: Write failing test for schedule parser

**Files:**
- Create: `tests/test_schedule_parser.py`

**Step 1: Write test**

Create `tests/test_schedule_parser.py`:

```python
"""Tests for natural language schedule parsing."""
import pytest
from ai_radio.schedule_parser import ScheduleParser


def test_parse_simple_schedule():
    """Test parsing a basic schedule description."""
    parser = ScheduleParser()

    result = parser.parse(
        "Monday through Friday at 9am, two hosts discuss Bitcoin and DeFi news"
    )

    assert result.name is not None
    assert result.format == "two_host_discussion"
    assert result.topic_area == "Bitcoin and DeFi news"
    assert 1 in result.days_of_week  # Monday
    assert 5 in result.days_of_week  # Friday
    assert result.start_time == "09:00"
    assert len(result.personas) == 2
```

**Step 2: Run test**

Run: `pytest tests/test_schedule_parser.py::test_parse_simple_schedule -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'ai_radio.schedule_parser'"

---

### Task 3.2: Implement ScheduleParser skeleton

**Files:**
- Create: `src/ai_radio/schedule_parser.py`

**Step 1: Create parser with Gemini**

Create `src/ai_radio/schedule_parser.py`:

```python
"""Natural language schedule parser using Gemini."""
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from google import genai

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ParsedSchedule:
    """Parsed schedule result."""
    name: str
    format: str
    topic_area: str
    days_of_week: List[int]
    start_time: str
    duration_minutes: int
    personas: List[Dict[str, str]]
    content_guidance: str


class ScheduleParser:
    """Parse natural language show schedules."""

    def __init__(self):
        self.client = genai.Client(api_key=config.gemini_api_key)

    def parse(self, user_input: str) -> ParsedSchedule:
        """Parse natural language to structured schedule.

        Args:
            user_input: Natural language schedule description

        Returns:
            ParsedSchedule with structured data
        """
        prompt = f"""Parse this radio show schedule into structured JSON:

"{user_input}"

Return ONLY valid JSON (no markdown, no explanation) with these exact fields:
{{
    "name": "Generated show name (short, descriptive)",
    "format": "interview" or "two_host_discussion",
    "topic_area": "What the show discusses",
    "days_of_week": [1,2,3,4,5],
    "start_time": "09:00",
    "duration_minutes": 8,
    "personas": [
        {{"name": "Person name", "traits": "personality traits"}},
        {{"name": "Another person", "traits": "personality traits"}}
    ],
    "content_guidance": "Topics/themes extracted from description"
}}

Days: 0=Sunday, 1=Monday, ..., 6=Saturday
Time: 24-hour format like "14:30"
Format: Use "interview" for host+expert, "two_host_discussion" for two hosts debating
"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )

        # Extract JSON from response
        text = response.text.strip()
        if text.startswith("```"):
            # Remove markdown code blocks
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text.strip())

        return ParsedSchedule(
            name=data["name"],
            format=data["format"],
            topic_area=data["topic_area"],
            days_of_week=data["days_of_week"],
            start_time=data["start_time"],
            duration_minutes=data.get("duration_minutes", 8),
            personas=data["personas"],
            content_guidance=data.get("content_guidance", "")
        )
```

**Step 2: Run test**

Run: `pytest tests/test_schedule_parser.py::test_parse_simple_schedule -v`
Expected: PASS (if Gemini API configured)

**Step 3: Commit**

```bash
git add src/ai_radio/schedule_parser.py tests/test_schedule_parser.py
git commit -m "feat: implement ScheduleParser with Gemini"
```

---

## Group 4: Show Generation Pipeline

### Task 4.1: Write test for topic research

**Files:**
- Create: `tests/test_show_generator.py`

**Step 1: Write test**

Create `tests/test_show_generator.py`:

```python
"""Tests for show generation pipeline."""
import pytest
from ai_radio.show_generator import research_topics


def test_research_topics():
    """Test researching topics for a show."""
    topics = research_topics(
        topic_area="Bitcoin news",
        content_guidance="Latest price movements and regulatory updates"
    )

    assert isinstance(topics, list)
    assert len(topics) > 0
    assert all(isinstance(t, str) for t in topics)
```

**Step 2: Run test**

Run: `pytest tests/test_show_generator.py::test_research_topics -v`
Expected: FAIL with "cannot import name 'research_topics'"

---

### Task 4.2: Implement topic research

**Files:**
- Create: `src/ai_radio/show_generator.py`

**Step 1: Implement research**

Create `src/ai_radio/show_generator.py`:

```python
"""Show generation pipeline orchestration."""
import logging
from typing import List
from google import genai

from .config import config

logger = logging.getLogger(__name__)


def research_topics(topic_area: str, content_guidance: str = "") -> List[str]:
    """Research current topics for a show.

    Args:
        topic_area: General topic area (e.g., "Bitcoin news")
        content_guidance: Optional specific topics/angles

    Returns:
        List of topic strings suitable for show discussion
    """
    client = genai.Client(api_key=config.gemini_api_key)

    prompt = f"""You are researching topics for an 8-minute radio show.

Topic Area: {topic_area}
{f'Content Guidance: {content_guidance}' if content_guidance else ''}

Research and return 3-5 current, interesting topics in this area.
Focus on recent developments, trends, or discussions.

Return as a JSON array of strings:
["Topic 1 description", "Topic 2 description", ...]

Be specific and concrete. Each topic should be a complete sentence.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt
    )

    import json
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    topics = json.loads(text.strip())
    logger.info(f"Researched {len(topics)} topics for {topic_area}")

    return topics
```

**Step 2: Run test**

Run: `pytest tests/test_show_generator.py::test_research_topics -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/ai_radio/show_generator.py tests/test_show_generator.py
git commit -m "feat: implement topic research with Gemini"
```

---

## CHECKPOINT: MVP Foundation Complete

**What We've Built:**
- ✅ Database schema (show_schedules, generated_shows)
- ✅ Data models (ShowSchedule, GeneratedShow)
- ✅ Repository layer (create/get schedules)
- ✅ Schedule parser (natural language → structured)
- ✅ Topic research (Gemini-based research)

**Next: Groups 5-6** will implement:
- Script generation (interview & discussion templates)
- Audio generation (Gemini TTS multi-speaker)
- Overnight service (batch generation)
- Liquidsoap integration (polling + enqueue)
- Error handling + retries

---

## Execution Options

**Plan saved to:** `docs/plans/2026-01-17-scheduled-shows-implementation.md`

**Two execution approaches:**

### Option 1: Subagent-Driven (This Session)
- **USE SKILL:** `superpowers:subagent-driven-development`
- Fresh subagent per task
- Code review between tasks
- Fast iteration

### Option 2: Parallel Session (Separate Session)
- **USE SKILL:** `superpowers:executing-plans` (in new session)
- Batch execution with checkpoints
- Can run in background

**Which approach do you prefer, CLiNT?**
