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
