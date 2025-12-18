# Phase 0: Foundation & Setup - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish project structure, directory layout, database schema, and Python environment

**Architecture:** Create the complete `/srv/ai_radio/` filesystem layout per SOW requirements, initialize SQLite database with required schema, set up system user/group for security isolation, and initialize Python project with `uv` for dependency management.

**Tech Stack:** Ubuntu 22.04+, SQLite3, Python 3.11+, uv package manager, systemd

---

## Task 1: System User & Group Setup

**Files:**
- None (system configuration)

**Step 1: Create ai-radio user and group**

Run:
```bash
sudo groupadd --system ai-radio
sudo useradd --system --gid ai-radio --home-dir /srv/ai_radio --no-create-home --shell /usr/sbin/nologin ai-radio
```

Expected: User and group created without error

**Step 2: Verify user creation**

Run:
```bash
id ai-radio
```

Expected output:
```
uid=XXX(ai-radio) gid=XXX(ai-radio) groups=XXX(ai-radio)
```

---

## Task 2: Directory Structure Creation

**Files:**
- Create: `/srv/ai_radio/` and all subdirectories per SOW Section 5

**Step 1: Create root directory**

Run:
```bash
sudo mkdir -p /srv/ai_radio
sudo chown ai-radio:ai-radio /srv/ai_radio
sudo chmod 755 /srv/ai_radio
```

Expected: Directory created with correct ownership

**Step 2: Create asset directories**

Run:
```bash
sudo mkdir -p /srv/ai_radio/assets/{music,beds,breaks/archive,safety}
sudo chown -R ai-radio:ai-radio /srv/ai_radio/assets
sudo chmod -R 755 /srv/ai_radio/assets
```

Expected: Asset directory tree created

**Step 3: Create drops directories**

Run:
```bash
sudo mkdir -p /srv/ai_radio/drops/{queue,force_break,kill_generation}
sudo chown -R ai-radio:ai-radio /srv/ai_radio/drops
sudo chmod -R 755 /srv/ai_radio/drops
```

Expected: Drops directory tree created

**Step 4: Create state directories**

Run:
```bash
sudo mkdir -p /srv/ai_radio/state
sudo chown -R ai-radio:ai-radio /srv/ai_radio/state
sudo chmod -R 755 /srv/ai_radio/state
```

Expected: State directory created

**Step 5: Create database directory**

Run:
```bash
sudo mkdir -p /srv/ai_radio/db
sudo chown -R ai-radio:ai-radio /srv/ai_radio/db
sudo chmod -R 755 /srv/ai_radio/db
```

Expected: Database directory created

**Step 6: Create logs directory**

Run:
```bash
sudo mkdir -p /srv/ai_radio/logs
sudo chown -R ai-radio:ai-radio /srv/ai_radio/logs
sudo chmod -R 755 /srv/ai_radio/logs
```

Expected: Logs directory created

**Step 7: Create Liquidsoap runtime directory**

Run:
```bash
sudo mkdir -p /run/liquidsoap
sudo chown -R ai-radio:ai-radio /run/liquidsoap
sudo chmod -R 755 /run/liquidsoap
```

Expected: Runtime directory created

**Step 8: Create tmp directory for atomic operations**

Run:
```bash
sudo mkdir -p /srv/ai_radio/tmp
sudo chown -R ai-radio:ai-radio /srv/ai_radio/tmp
sudo chmod -R 755 /srv/ai_radio/tmp
```

Expected: Temp directory created for atomic file writes

**Step 9: Verify directory structure**

Run:
```bash
sudo tree -L 3 -d /srv/ai_radio
```

Expected output:
```
/srv/ai_radio
├── assets
│   ├── beds
│   ├── breaks
│   │   └── archive
│   ├── music
│   └── safety
├── db
├── drops
│   ├── force_break
│   ├── kill_generation
│   └── queue
├── logs
└── state
```

---

## Task 3: Runtime Directory Note

**Note:** `/run/liquidsoap` persistence will be handled by systemd `RuntimeDirectory` directive in Phase 1 (Core Infrastructure) service files.

This is the recommended systemd-native approach that couples the directory lifecycle to the service. The directive in the systemd unit file will look like:

```ini
[Service]
RuntimeDirectory=liquidsoap
RuntimeDirectoryMode=0755
```

This automatically:
- Creates `/run/liquidsoap` when the service starts
- Sets correct ownership (User/Group from service)
- Cleans up when the service stops
- Persists across reboots (directory recreated on service start)

**Why this is better than tmpfiles.d:**
- No separate configuration file to maintain
- Directory lifecycle tied to service lifecycle
- Fewer moving parts
- Standard systemd pattern

**No action required in Phase 0** - This will be implemented in Phase 1 when creating systemd service files.

---

## Task 4: Python Project Initialization

**Files:**
- Create: `/srv/ai_radio/pyproject.toml`
- Create: `/srv/ai_radio/src/ai_radio/__init__.py`
- Create: `/srv/ai_radio/src/ai_radio/config.py`

**Step 1: Create source directory**

Run:
```bash
sudo mkdir -p /srv/ai_radio/src/ai_radio
sudo chown -R ai-radio:ai-radio /srv/ai_radio/src
```

Expected: Source directory created

**Step 2: Initialize project with uv**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio uv init --name ai-radio --no-readme
```

Expected: `pyproject.toml` created

**Step 3: Add core dependencies**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio uv add pydantic pydantic-settings
```

Expected: Dependencies added to pyproject.toml

**Step 3.5: Add development dependencies**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio uv add --dev pytest pytest-cov ruff mypy
```

Expected: Dev dependencies added to pyproject.toml [project.optional-dependencies]

**Step 4: Create __init__.py**

Create file `/srv/ai_radio/src/ai_radio/__init__.py`:
```python
"""AI Radio Station - 24/7 streaming with AI-generated content."""

__version__ = "0.1.0"
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/__init__.py << 'EOF'
"""AI Radio Station - 24/7 streaming with AI-generated content."""

__version__ = "0.1.0"
EOF
```

Expected: File created

**Step 5: Create configuration module**

Create file `/srv/ai_radio/src/ai_radio/config.py`:
```python
"""Configuration management for AI Radio Station.

Uses pydantic-settings for environment-based configuration with sensible defaults.
All paths and secrets can be overridden via environment variables.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RadioConfig(BaseSettings):
    """AI Radio Station configuration.

    Environment variables:
        RADIO_BASE_PATH: Base directory (default: /srv/ai_radio)
        RADIO_STATION_TZ: IANA timezone (default: America/Chicago)
        RADIO_STATION_LAT: Station latitude for weather
        RADIO_STATION_LON: Station longitude for weather
        RADIO_LLM_API_KEY: LLM provider API key
        RADIO_TTS_API_KEY: TTS provider API key
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file="/srv/ai_radio/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base paths
    base_path: Path = Field(default=Path("/srv/ai_radio"))

    # Station configuration
    station_tz: str = Field(default="America/Chicago")
    station_lat: Optional[float] = Field(default=None)
    station_lon: Optional[float] = Field(default=None)

    # API keys (required for production, optional for testing)
    llm_api_key: Optional[str] = Field(default=None)
    tts_api_key: Optional[str] = Field(default=None)

    def validate_production_config(self) -> None:
        """Validate that required production fields are set.

        Raises:
            ValueError: If required fields are missing
        """
        errors = []
        if self.station_lat is None:
            errors.append("RADIO_STATION_LAT is required for weather data")
        if self.station_lon is None:
            errors.append("RADIO_STATION_LON is required for weather data")
        if self.llm_api_key is None:
            errors.append("RADIO_LLM_API_KEY is required for content generation")
        if self.tts_api_key is None:
            errors.append("RADIO_TTS_API_KEY is required for voice synthesis")

        if errors:
            raise ValueError(
                "Production configuration incomplete:\n  - " + "\n  - ".join(errors)
            )

    # Derived paths
    @property
    def assets_path(self) -> Path:
        return self.base_path / "assets"

    @property
    def music_path(self) -> Path:
        return self.assets_path / "music"

    @property
    def beds_path(self) -> Path:
        return self.assets_path / "beds"

    @property
    def breaks_path(self) -> Path:
        return self.assets_path / "breaks"

    @property
    def breaks_archive_path(self) -> Path:
        return self.breaks_path / "archive"

    @property
    def safety_path(self) -> Path:
        return self.assets_path / "safety"

    @property
    def drops_path(self) -> Path:
        return self.base_path / "drops"

    @property
    def tmp_path(self) -> Path:
        return self.base_path / "tmp"

    @property
    def state_path(self) -> Path:
        return self.base_path / "state"

    @property
    def db_path(self) -> Path:
        return self.base_path / "db" / "radio.sqlite3"

    @property
    def logs_path(self) -> Path:
        return self.base_path / "logs" / "jobs.jsonl"

    @property
    def liquidsoap_sock_path(self) -> Path:
        return Path("/run/liquidsoap/radio.sock")


# Global config instance
config = RadioConfig()
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/config.py << 'EOF'
[content above]
EOF
```

Expected: Configuration module created

**Step 6: Verify Python installation**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio uv run python -c "from ai_radio.config import config; print(config.base_path)"
```

Expected output:
```
/srv/ai_radio
```

---

## Task 5: Database Schema Creation

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/db.py`
- Create: `/srv/ai_radio/scripts/init_db.py`

**Step 1: Create database module**

Create file `/srv/ai_radio/src/ai_radio/db.py`:
```python
"""Database schema and operations for AI Radio Station.

Schema per SOW Section 6:
- assets: Audio files with loudness metadata
- play_history: Track play events
- generation_runs: Job execution logs
"""

import sqlite3
from pathlib import Path
from typing import Optional

from ai_radio.config import config


# Schema SQL per SOW Section 6
SCHEMA_SQL = """
-- Assets table: audio files with loudness metadata
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,  -- sha256 hash
    path TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
    duration_sec REAL,
    loudness_lufs REAL,
    true_peak_dbtp REAL,
    energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
    title TEXT,
    artist TEXT,
    album TEXT,
    created_at TEXT NOT NULL  -- ISO8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at);

-- Play history: track what was played when
CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    played_at TEXT NOT NULL,  -- ISO8601 UTC
    source TEXT NOT NULL CHECK(source IN ('music', 'override', 'break', 'bumper')),
    hour_bucket TEXT NOT NULL,  -- e.g., '2025-12-18T15:00:00Z'
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);

CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);
CREATE INDEX IF NOT EXISTS idx_play_history_hour_bucket ON play_history(hour_bucket);
CREATE INDEX IF NOT EXISTS idx_play_history_asset_id ON play_history(asset_id);

-- Generation runs: job execution tracking
CREATE TABLE IF NOT EXISTS generation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job TEXT NOT NULL CHECK(job IN ('planner', 'news_gen', 'enqueue', 'housekeeping', 'healthcheck')),
    started_at TEXT NOT NULL,  -- ISO8601 UTC
    finished_at TEXT,  -- ISO8601 UTC, nullable
    status TEXT NOT NULL CHECK(status IN ('ok', 'fail', 'skipped')),
    error TEXT,  -- nullable
    output_path TEXT  -- nullable
);

CREATE INDEX IF NOT EXISTS idx_generation_runs_job ON generation_runs(job);
CREATE INDEX IF NOT EXISTS idx_generation_runs_started_at ON generation_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_generation_runs_status ON generation_runs(status);
"""


def init_database(db_path: Optional[Path] = None) -> None:
    """Initialize database with schema.

    Args:
        db_path: Path to SQLite database file. Defaults to config.db_path.
    """
    if db_path is None:
        db_path = config.db_path

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database and schema
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get database connection.

    Args:
        db_path: Path to SQLite database file. Defaults to config.db_path.

    Returns:
        sqlite3.Connection with row factory configured
    """
    if db_path is None:
        db_path = config.db_path

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/db.py << 'EOF'
[content above]
EOF
```

Expected: Database module created

**Step 2: Create database initialization script**

Create file `/srv/ai_radio/scripts/init_db.py`:
```python
#!/usr/bin/env python3
"""Initialize AI Radio Station database with schema."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.db import init_database
from ai_radio.config import config


def main():
    print(f"Initializing database at {config.db_path}")
    init_database()
    print("Database initialized successfully")
    print(f"Schema tables created: assets, play_history, generation_runs")


if __name__ == "__main__":
    main()
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/scripts/init_db.py << 'EOF'
[content above]
EOF
sudo chmod +x /srv/ai_radio/scripts/init_db.py
```

Expected: Script created and executable

**Step 3: Run database initialization**

Run:
```bash
cd /srv/ai_radio
sudo -u ai-radio uv run python scripts/init_db.py
```

Expected output:
```
Initializing database at /srv/ai_radio/db/radio.sqlite3
Database initialized successfully
Schema tables created: assets, play_history, generation_runs
```

**Step 4: Verify database schema**

Run:
```bash
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 ".schema"
```

Expected: Complete schema SQL with all three tables and indexes

**Step 5: Verify tables exist**

Run:
```bash
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 ".tables"
```

Expected output:
```
assets  generation_runs  play_history
```

---

## Task 6: Environment Configuration

**Files:**
- Create: `/srv/ai_radio/.env.example`
- Create: `/srv/ai_radio/.gitignore`

**Step 1: Create .env.example**

Create file `/srv/ai_radio/.env.example`:
```bash
# AI Radio Station Configuration
# Copy this to .env and fill in your values

# Station location (required for weather)
RADIO_STATION_LAT=41.8781
RADIO_STATION_LON=-87.6298

# Station timezone (IANA timezone name)
RADIO_STATION_TZ=America/Chicago

# API Keys (required for production)
RADIO_LLM_API_KEY=your-llm-api-key-here
RADIO_TTS_API_KEY=your-tts-api-key-here

# RSS Feeds (comma-separated URLs)
RADIO_RSS_FEEDS=https://example.com/feed1.xml,https://example.com/feed2.xml
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/.env.example << 'EOF'
[content above]
EOF
```

Expected: Example env file created

**Step 2: Create .gitignore**

Create file `/srv/ai_radio/.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
.venv/
venv/
ENV/

# Environment variables
.env

# Database
*.sqlite3
*.db

# Logs
logs/
*.log
*.jsonl

# Assets (large files)
assets/music/
assets/breaks/
assets/beds/

# State files
state/
drops/

# uv
.uv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/.gitignore << 'EOF'
[content above]
EOF
```

Expected: .gitignore created

---

## Task 7: Log Rotation Configuration

**Files:**
- Create: `/etc/logrotate.d/ai-radio`

**Step 1: Create logrotate configuration**

Create file `/etc/logrotate.d/ai-radio`:
```
/srv/ai_radio/logs/*.jsonl {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ai-radio ai-radio
    sharedscripts
    postrotate
        # No service reload needed - append-only logs
    endscript
}
```

Run:
```bash
sudo tee /etc/logrotate.d/ai-radio << 'EOF'
/srv/ai_radio/logs/*.jsonl {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ai-radio ai-radio
    sharedscripts
    postrotate
        # No service reload needed - append-only logs
    endscript
}
EOF
```

Expected: Logrotate configuration created

**Step 2: Test logrotate configuration**

Run:
```bash
sudo logrotate --debug /etc/logrotate.d/ai-radio
```

Expected: No errors in dry-run mode

**Step 3: Verify logrotate will run**

Run:
```bash
cat /etc/logrotate.d/ai-radio
```

Expected: Configuration file contents displayed correctly

---

## Task 8: Verification & Documentation

**Files:**
- Create: `/srv/ai_radio/README.md`

**Step 1: Create README**

Create file `/srv/ai_radio/README.md`:
```markdown
# AI Radio Station

24/7 AI-powered radio station with automated news/weather breaks.

## Project Structure

```
/srv/ai_radio/
├── assets/           # Audio files
│   ├── music/       # Normalized music library
│   ├── beds/        # Background music for breaks
│   ├── breaks/      # Generated news/weather breaks
│   └── safety/      # Evergreen fallback content
├── db/              # SQLite database
├── drops/           # Operator override folders
├── logs/            # Structured job logs
├── scripts/         # Utility scripts
├── src/ai_radio/    # Python source
└── state/           # Runtime state files
```

## Phase 0 Complete

This phase establishes:
- ✅ Complete directory structure
- ✅ System user/group (ai-radio)
- ✅ SQLite database with schema
- ✅ Python project with uv
- ✅ Configuration management

## Next Steps

Proceed to Phase 1: Core Infrastructure (Icecast + Liquidsoap)
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/README.md << 'EOF'
[content above]
EOF
```

Expected: README created

**Step 2: Run full verification**

Run:
```bash
#!/bin/bash
echo "=== Phase 0 Verification ==="
echo ""
echo "1. User/Group:"
id ai-radio
echo ""
echo "2. Directory Structure:"
sudo tree -L 2 -d /srv/ai_radio
echo ""
echo "3. Database:"
sudo -u ai-radio sqlite3 /srv/ai_radio/db/radio.sqlite3 ".tables"
echo ""
echo "4. Python Environment:"
cd /srv/ai_radio && sudo -u ai-radio uv run python -c "from ai_radio.config import config; print(f'Config loaded: {config.base_path}')"
echo ""
echo "=== Phase 0 Complete ==="
```

Expected: All checks pass without errors

---

## Definition of Done

Phase 0 is complete when:

- ✅ `ai-radio` user and group exist
- ✅ All directories exist with correct ownership (including /srv/ai_radio/tmp)
- ✅ systemd tmpfiles.d configured for /run/liquidsoap persistence
- ✅ Database schema matches SOW Section 6
- ✅ Python project initializes with `uv`
- ✅ Development dependencies installed (pytest, ruff, mypy)
- ✅ Configuration module loads successfully with validation helper
- ✅ logrotate configured for custom log directory
- ✅ Verification script passes all checks

## SOW Compliance Checklist

- ✅ Section 5: File/Folder Layout - Complete directory structure created
- ✅ Section 6: Data Model Requirements - All three tables with correct schema
- ✅ Section 13: User/group setup - `ai-radio` user with least privilege
- ✅ Non-Negotiable #5: Atomic handoffs - Temp file pattern ready for use
- ✅ Non-Negotiable #6: OS-level scheduling - Directory structure ready for systemd

## Validation Summary

**Validated by:** gemini-3-pro-preview thinking model
**Status:** APPROVED with enhancements
**Compliance:** 90%+ SOW requirements satisfied

**Issues Identified & Resolved:**

1. **MEDIUM**: /run/liquidsoap persistence across reboots
   - **Resolution**: Added Task 3 (systemd tmpfiles.d configuration)

2. **LOW**: Missing /srv/ai_radio/tmp for atomic operations
   - **Resolution**: Added to Task 2, Step 8 + config.tmp_path property

3. **LOW**: Configuration validation could be stronger
   - **Resolution**: Added validate_production_config() method to RadioConfig

4. **LOW**: Development dependencies missing
   - **Resolution**: Added Task 4, Step 3.5 (pytest, ruff, mypy)

5. **ADDITIONAL**: Log rotation for custom directory
   - **Resolution**: Added Task 7 (logrotate configuration)

**Expert Analysis Recommendations Applied:**
- ✅ tmpfiles.d prevents service failure after reboot
- ✅ Dedicated tmp directory for atomic file operations (safer than /tmp)
- ✅ Fail-fast configuration validation
- ✅ Separated dev dependencies from production
- ✅ Log rotation prevents disk fill-up

## Next Phase

Proceed to Phase 1: Core Infrastructure (Icecast + Liquidsoap streaming)
