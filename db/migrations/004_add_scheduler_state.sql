-- Migration: Add scheduler_state table for tracking scheduled events
-- Replaces file-based state with database state for consistency

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS scheduler_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL  -- ISO8601 UTC
);

-- Index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_scheduler_state_updated_at ON scheduler_state(updated_at);

COMMIT;
