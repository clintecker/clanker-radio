-- AI Radio Database Schema
-- Phase 2: Asset Management

-- Assets table stores metadata and technical details for all audio files
CREATE TABLE IF NOT EXISTS assets (
    -- Content-addressable ID (SHA256 hash of file contents)
    id TEXT PRIMARY KEY,

    -- File system path (must be unique)
    path TEXT UNIQUE NOT NULL,

    -- Asset classification: music, break, bed, safety
    kind TEXT NOT NULL,

    -- Duration in seconds
    duration_sec REAL NOT NULL,

    -- EBU R128 integrated loudness in LUFS
    loudness_lufs REAL,

    -- True peak level in dBTP
    true_peak_dbtp REAL,

    -- Energy classification (0-100 scale, for future scheduling)
    energy_level INTEGER,

    -- Metadata from audio tags
    title TEXT,
    artist TEXT,
    album TEXT,

    -- Record creation timestamp (ISO 8601 format with timezone)
    created_at TEXT NOT NULL
);

-- Index for efficient lookups by path
CREATE INDEX IF NOT EXISTS idx_assets_path ON assets(path);

-- Index for filtering by kind (music, break, etc.)
CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);

-- Index for filtering by energy level (future scheduling feature)
CREATE INDEX IF NOT EXISTS idx_assets_energy ON assets(energy_level);
