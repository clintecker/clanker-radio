-- Migration: Add 'bumper' to assets.kind CHECK constraint
-- Date: 2025-12-28
-- Purpose: Enable ingestion of station IDs and bumpers into assets table

-- SQLite doesn't support ALTER TABLE ... ALTER COLUMN to modify CHECK constraints
-- We need to recreate the table with the new constraint

BEGIN TRANSACTION;

-- Create new table with updated constraint
CREATE TABLE assets_new (
    id TEXT PRIMARY KEY,  -- sha256 hash or filename stem for bumpers/breaks
    path TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety', 'bumper')),
    duration_sec REAL,
    loudness_lufs REAL,
    true_peak_dbtp REAL,
    energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
    title TEXT,
    artist TEXT,
    album TEXT,
    created_at TEXT NOT NULL  -- ISO8601 UTC
);

-- Copy existing data
INSERT INTO assets_new
SELECT * FROM assets;

-- Drop old table
DROP TABLE assets;

-- Rename new table
ALTER TABLE assets_new RENAME TO assets;

-- Recreate indexes
CREATE INDEX idx_assets_kind ON assets(kind);
CREATE INDEX idx_assets_created_at ON assets(created_at);
CREATE UNIQUE INDEX idx_assets_path_unique ON assets(path);

COMMIT;
