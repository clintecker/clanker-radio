# Unified Asset Ingestion System - Design Document

**Date**: 2025-12-28
**Status**: Approved
**Validated By**: PAL (Gemini 2.5 Pro)

## Overview & Goals

**Objective**: Eliminate runtime ffprobe calls and path construction complexity by ensuring all playable assets (music, bumpers, breaks) exist in the `assets` table before playback.

**Core Principle**: Content-addressable storage using SHA256. Identical audio content = same asset ID, regardless of filename.

### Key Design Decisions

1. **Unified ID scheme**: All assets use SHA256 content hashes as IDs (computed from audio file contents)
2. **Single source of truth**: `assets` table contains metadata for everything that can play
3. **Ingest-time processing**: Heavy lifting (duration calculation, normalization) happens once during ingestion
4. **Automatic workflows**: Breaks auto-ingest after generation; old breaks auto-cleanup after 48 hours
5. **Fix existing bug**: Current ingest.py checks deduplication by file path, not content hash

### Benefits

- `export_now_playing.py` simplifies dramatically - just JOIN assets table, no ffprobe or path guessing
- `play_history.source` can be populated directly from `assets.kind`
- Consistent querying regardless of asset type
- Performance improvement: eliminate ~200ms ffprobe calls per station ID export
- True content-based deduplication across all asset types

### Migration Path

1. Add 'bumper' to assets.kind CHECK constraint (schema change)
2. Compute SHA256 for all existing bumpers/breaks
3. Batch-ingest bumpers/breaks into assets table
4. Migrate play_history records (filename stems → SHA256 IDs)
5. Update scripts (export, enqueue, generate, cleanup, record_play)
6. Add foreign key constraint for referential integrity

---

## Database Migration Strategy

### Schema Changes

**SQLite-specific table recreation** (already created in `migrations/001_add_bumper_kind.sql`):
```sql
-- Add 'bumper' to kind constraint via table recreation
CREATE TABLE assets_new (...
    kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety', 'bumper')),
    ...
);
-- Copy data, drop old table, rename new table
```

**Post-migration additions**:
```sql
-- Add index for performance
CREATE INDEX idx_play_history_played_at ON play_history(played_at);

-- Add foreign key constraint
ALTER TABLE play_history
  ADD CONSTRAINT fk_play_history_asset
  FOREIGN KEY (asset_id) REFERENCES assets(id);
```

### Migration Script Flow

**Script**: `scripts/migrate_to_sha256_ids.py`

**Pre-flight**:
1. Create backup: `cp radio.db radio.db.bak-pre-migration`
2. Run dry-run analysis to identify all non-SHA256 IDs:
   ```sql
   SELECT DISTINCT asset_id FROM play_history WHERE length(asset_id) != 64;
   ```

**Migration** (wrapped in single transaction):
1. **Discover & hash**: Scan `assets/bumpers/` and `assets/breaks/`, compute SHA256 for each file
2. **Build mapping**: Create `filename_stem → SHA256` dictionary (e.g., `"station_id_10" → "abc123..."`)
3. **Batch ingest**: Call `ingest_audio_file(ingest_existing=True)` for each bumper/break
4. **Handle orphans**: If file missing, create synthetic asset record:
   ```python
   {
     "id": f"orphan_{filename_stem}",  # Human-readable prefix
     "path": f"/dev/null/deleted/{filename_stem}",
     "title": f"[Deleted Asset] {filename_stem}",
     "duration_sec": 0,
     "kind": "bumper" or "break"
   }
   ```
5. **Migrate play_history**: Single UPDATE with CASE expression for efficiency:
   ```sql
   UPDATE play_history
   SET asset_id = CASE asset_id
     WHEN 'station_id_10' THEN 'sha256_for_10'
     WHEN 'break_20251222' THEN 'sha256_for_break'
     -- ... all mappings
     ELSE asset_id
   END
   WHERE asset_id IN ('station_id_10', 'break_20251222', ...);
   ```
6. **Log mapping**: Write `migration_mapping.json` for audit trail and potential analysis

**Post-validation**:
```sql
-- Must return 0 before adding foreign key
SELECT count(*) FROM play_history ph
LEFT JOIN assets a ON ph.asset_id = a.id
WHERE a.id IS NULL;

-- Verify all old IDs migrated (should return 0)
SELECT count(*) FROM play_history
WHERE length(asset_id) != 64 AND asset_id NOT LIKE 'orphan_%';
```

**Safety Features**:
- All wrapped in transaction (rollback on any failure)
- Orphan records preserve historical data with clear markers
- Mapping log enables audit and analysis
- Mandatory database backup before execution

---

## Ingestion API Changes

### Modified Function Signature

**File**: `src/ai_radio/ingest.py`

```python
from typing import Optional

def ingest_audio_file(
    source_path: Path,
    kind: str,
    db_path: Path,
    output_dir: Optional[Path] = None,  # Renamed from music_dir, now optional
    target_lufs: float = -18.0,
    true_peak: float = -1.0,
    ingest_existing: bool = False,  # NEW parameter
) -> dict:
    """Ingest audio file into asset library.

    Args:
        ingest_existing: If True, skip normalization and register existing file in-place
        output_dir: Required when ingest_existing=False, ignored otherwise
    """
    if not ingest_existing and output_dir is None:
        raise ValueError("output_dir is required when creating a new asset")
```

### Key Changes

**1. Fix deduplication bug** (current issue at line 71):
```python
# BEFORE (WRONG - checks by path):
existing = get_asset_by_path(conn, source_path)

# AFTER (CORRECT - checks by content hash):
metadata = extract_metadata(source_path)
asset_id = metadata.sha256_id
existing = get_asset_by_id(conn, asset_id)  # NEW function in db_assets.py
if existing:
    return existing  # True content-based deduplication
```

**2. New helper function** (`src/ai_radio/audio.py`):
```python
def measure_loudness(input_path: Path) -> dict:
    """Measure audio loudness without creating an output file.

    Uses ffmpeg-normalize in dry-run mode to get EBU R128 stats.

    Args:
        input_path: Source audio file

    Returns:
        dict with loudness_lufs and true_peak_dbtp values

    Raises:
        ValueError: If measurement fails or stats cannot be parsed
    """
    cmd = [
        "ffmpeg-normalize",
        str(input_path),
        "-n",  # No-op / dry-run mode
        "-f",  # Force overwrite
        "--normalization-type", "ebu",
        "--print-stats",
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    # Parse loudness_lufs and true_peak_dbtp from output
    # Return {"loudness_lufs": float, "true_peak_dbtp": float}
```

**3. Branch logic in ingest_audio_file**:

- **When `ingest_existing=False`** (current behavior for music):
  1. Extract metadata
  2. Check SHA256 deduplication
  3. Normalize audio
  4. Copy to output_dir
  5. Insert into database

- **When `ingest_existing=True`** (new behavior for bumpers/breaks):
  1. Extract metadata
  2. Check SHA256 deduplication
  3. Measure loudness without transcoding (via `measure_loudness()`)
  4. Use `source_path` as-is for `assets.path`
  5. Insert into database

**Safety**: Loudness measurement failures are hard errors. No bypass flag - complete metadata or fail.

---

## Integration Points

### Scripts to Modify

**1. `scripts/generate_break.py`** - Auto-ingest after generation
```python
# After generating break audio file
break_path = config.breaks_path / f"break_{timestamp}.mp3"
generate_audio(break_path)  # existing logic

# NEW: Auto-ingest immediately (ingestion failure = script failure)
try:
    from ai_radio.ingest import ingest_audio_file
    ingest_audio_file(
        source_path=break_path,
        kind="break",
        db_path=config.db_path,
        ingest_existing=True,  # Already at correct loudness
    )
except Exception as e:
    logger.error(f"Failed to ingest break: {e}")
    return 1  # Fail loudly for systemd alerting
```

**2. `scripts/enqueue_station_id.py`** - Query database instead of filesystem
```python
# BEFORE: Scan filesystem
all_station_ids = sorted(BUMPERS_DIR.glob("station_id_*.*"))
selected = random.choice(all_station_ids)

# AFTER: Query database with anti-repeat logic
cursor.execute("""
    SELECT id, path FROM assets
    WHERE kind = 'bumper'
    AND id NOT IN (
        SELECT asset_id FROM play_history
        WHERE played_at > datetime('now', '-1 hour')
    )
""")
all_station_ids = cursor.fetchall()
selected = random.choice(all_station_ids)
```

**3. `scripts/cleanup_old_breaks.py`** - NEW daily cron job
```python
#!/usr/bin/env python3
"""Cleanup breaks older than 48 hours."""

# Portable SQL pattern (no RETURNING clause)
cursor.execute(
    "SELECT path FROM assets WHERE kind = 'break' AND created_at < datetime('now', '-48 hours')"
)
paths_to_delete = [row[0] for row in cursor.fetchall()]

if not paths_to_delete:
    return  # Nothing to do

# Delete from database
placeholders = ','.join('?' for _ in paths_to_delete)
cursor.execute(f"DELETE FROM assets WHERE path IN ({placeholders})", paths_to_delete)
conn.commit()

# Unlink files from disk
for path in paths_to_delete:
    try:
        Path(path).unlink()
        logger.info(f"Deleted: {path}")
    except OSError as e:
        logger.error(f"Error deleting {path}: {e}")

# Support --dry-run flag for safety
```

**4. `scripts/record_play.py`** - Write SHA256 IDs to play_history
```python
# CRITICAL UPDATE: Record plays with SHA256 asset_id

# Liquidsoap passes file path
file_path = sys.argv[1]  # e.g., /srv/ai_radio/assets/bumpers/station_id_10.mp3

# Look up asset by path to get SHA256 ID
conn = sqlite3.connect(config.db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, kind FROM assets WHERE path = ?", (file_path,))
row = cursor.fetchone()

if not row:
    logger.error(f"Asset not found in database: {file_path}")
    return 1

asset_id, asset_kind = row

# Write to play_history with SHA256 ID and kind from assets table
cursor.execute(
    "INSERT INTO play_history (asset_id, source, played_at) VALUES (?, ?, ?)",
    (asset_id, asset_kind, datetime.now(timezone.utc).isoformat())
)
conn.commit()
```

**5. `scripts/export_now_playing.py`** - Dramatically simplified

See next section for details.

### Station ID Workflow (Manual Creation)

Station IDs are created manually by user:
1. User produces `station_id_XX.mp3` or `.wav` manually
2. Run `batch_ingest_assets.py --kind bumper` to register in database
3. Files stay in place (since `ingest_existing=True`)
4. `assets.path` = original path, `assets.id` = SHA256 hash
5. Enqueue script queries database to select station IDs

**No Liquidsoap changes needed**: Liquidsoap passes file paths → `record_play.py` looks up SHA256 → writes to play_history

---

## Simplified export_now_playing.py

### Before (Current Complexity)

- Two code paths: Liquidsoap metadata vs. fallback
- Path construction from asset_id + directory + extension guessing
- Runtime ffprobe calls for duration
- COALESCE and CASE expressions for missing metadata
- ~150 lines of conditional logic

### After (Simplified)

**Keep stream-level fallbacks**:
- "Technical Difficulties" (fallback_mode from Icecast)
- "Station Starting Up" (startup_mode from Icecast)

**Simplified core query**:
```python
def get_current_playing():
    """Get current track from play_history + assets LEFT JOIN."""
    from datetime import datetime, timezone, timedelta

    # Compute cutoff in Python for timestamp format compatibility
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    cursor.execute("""
        SELECT
            a.id, a.title, a.artist, a.album,
            a.duration_sec, ph.played_at, a.kind
        FROM play_history ph
        LEFT JOIN assets a ON ph.asset_id = a.id
        WHERE ph.played_at >= ?
        ORDER BY ph.played_at DESC
        LIMIT 1
    """, (cutoff,))

    row = cursor.fetchone()

    if not row:
        return None

    # Graceful degradation for deleted assets
    if row[1] is None:  # title is NULL = deleted asset
        return {
            "asset_id": row[0],
            "title": "[Deleted Track]",
            "artist": "Unknown",
            "album": None,
            "duration_sec": 0,
            "played_at": row[5],
            "source": "unknown"
        }

    return {
        "asset_id": row[0],
        "title": row[1],
        "artist": row[2],
        "album": row[3],
        "duration_sec": row[4],
        "played_at": row[5],
        "source": row[6]
    }
```

### Eliminated

- All ffprobe calls (~200ms overhead each)
- Path construction logic
- Fallback metadata queries
- Extension guessing loops
- COALESCE/CASE expressions for metadata
- Sleep buffers and race condition handling

### Result

- ~50 lines (down from ~150)
- Single SQL query (< 1ms with index)
- Zero runtime overhead
- Resilient to deleted assets (LEFT JOIN + null handling)

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_ingest.py`

```python
def test_ingest_existing_skips_normalization(tmp_path):
    """Verify ingest_existing=True doesn't transcode."""
    source = create_test_audio(tmp_path / "test.mp3")
    result = ingest_audio_file(source, kind="bumper", ingest_existing=True)
    assert result['path'] == str(source)  # Same file, not copied
    assert result['loudness_lufs'] is not None  # But still measured

def test_deduplication_by_content():
    """Verify SHA256-based deduplication."""
    result1 = ingest_audio_file(file1, kind="bumper")
    result2 = ingest_audio_file(file2, kind="bumper")  # Identical content
    assert result1['id'] == result2['id']  # Same SHA256
    assert result1 == result2  # Returned existing record

def test_orphan_handling_in_migration():
    """Verify synthetic assets created for missing files."""
    # Setup: station_id_99 in play_history, file missing
    migrate_to_sha256()
    asset = get_asset_by_id("orphan_station_id_99")
    assert asset['title'] == "[Deleted Asset] station_id_99"
    assert asset['path'].startswith("/dev/null/deleted/")

def test_cleanup_script_selects_correct_records():
    """Verify cleanup only targets old breaks."""
    # Setup: Create old and new break assets
    old_break = create_asset(kind="break", created_at=now - 50.hours)
    new_break = create_asset(kind="break", created_at=now - 10.hours)

    # Execute cleanup logic (48-hour threshold)
    deleted = cleanup_old_breaks()

    assert old_break.id in deleted
    assert new_break.id not in deleted

def test_cleanup_dry_run_makes_no_changes():
    """Verify --dry-run doesn't delete anything."""
    old_break = create_asset(kind="break", created_at=now - 50.hours)

    cleanup_old_breaks(dry_run=True)

    assert asset_exists(old_break.id)
    assert file_exists(old_break.path)
```

### Integration Tests

**File**: `tests/test_migration.py`

```python
def test_full_migration_workflow(test_db):
    """End-to-end migration test with production data copy."""
    # Setup: Use copy of production database with real data
    # Execute: Run migration script
    # Verify: All filename stem IDs converted to SHA256
    # Verify: Foreign key constraint satisfied (no orphans)
    # Verify: Mapping log created with correct count

def test_record_play_writes_sha256_ids():
    """Verify new plays use SHA256 IDs after migration."""
    # Setup: Ingest a test bumper
    bumper = ingest_audio_file(test_file, kind="bumper", ingest_existing=True)

    # Simulate: Liquidsoap play event
    record_play(bumper['path'])

    # Verify: play_history has SHA256 asset_id, not filename stem
    plays = get_recent_plays()
    assert plays[0]['asset_id'] == bumper['id']  # SHA256
    assert plays[0]['source'] == 'bumper'  # From assets.kind

def test_enqueue_anti_repeat_logic():
    """Verify anti-repeat logic works after migration."""
    # Setup: Create play_history for bumper_A (1 hour ago)
    bumper_a = create_asset(kind="bumper")
    create_play(asset_id=bumper_a.id, played_at=now - 1.hour)

    # Execute: Select station ID
    selected = select_station_id()

    # Verify: bumper_A not selected (within 1-hour window)
    assert selected.id != bumper_a.id
```

### Performance Benchmarks

Measure before and after migration:

```bash
# Before migration
$ time ./scripts/export_now_playing.py
real    0m0.215s  # ~200ms for ffprobe call

# After migration
$ time ./scripts/export_now_playing.py
real    0m0.005s  # <5ms for simple JOIN query

# Expected improvement: 40-50x faster
```

### Manual Testing Checklist

1. ✅ **Backup database**: `cp radio.db radio.db.bak-pre-migration`
2. ✅ **Run migration on staging** with production data copy
3. ✅ **Verify export output**: Compare pre/post migration JSON output for same play_history
4. ✅ **Test station ID playback**: Play station ID, verify metadata appears within 2s in frontend
5. ✅ **Test break generation flow**: Generate break → auto-ingest → queue → play → display
6. ✅ **Verify cleanup**: Wait 48hrs (or manipulate timestamps), verify old breaks deleted
7. ✅ **Verify anti-repeat**: Play same station ID twice, verify not selected within 1hr window

### Rollback Plan

**Components**:
- `radio.db.bak-pre-migration` - Full database backup
- `migration_mapping.json` - Audit log of all ID transformations

**Rollback Procedure** (if issues found):
1. Stop all services: `systemctl stop ai-radio-*`
2. Restore database: `cp radio.db.bak-pre-migration radio.db`
3. Revert code changes in all affected scripts
4. Restart services: `systemctl start ai-radio-*`

**Critical**: Database and code must be rolled back together. Cannot run old code with new database or vice versa.

---

## Implementation Checklist

### Phase 1: Database & Core API
- [ ] Run schema migration (001_add_bumper_kind.sql)
- [ ] Add `get_asset_by_id()` to db_assets.py
- [ ] Add `measure_loudness()` to audio.py
- [ ] Modify `ingest_audio_file()` to support `ingest_existing` parameter
- [ ] Fix deduplication bug (check SHA256 first, not path)
- [ ] Write unit tests for new functions

### Phase 2: Migration Script
- [ ] Create `scripts/migrate_to_sha256_ids.py`
- [ ] Implement dry-run analysis
- [ ] Implement mapping generation (filename_stem → SHA256)
- [ ] Implement batch ingestion with orphan handling
- [ ] Implement play_history UPDATE with CASE expression
- [ ] Add transaction wrapping and error handling
- [ ] Write integration tests

### Phase 3: Script Updates
- [ ] Update `scripts/generate_break.py` (auto-ingest)
- [ ] Update `scripts/enqueue_station_id.py` (query DB)
- [ ] Create `scripts/cleanup_old_breaks.py` (with --dry-run)
- [ ] Update `scripts/record_play.py` (write SHA256 IDs)
- [ ] Simplify `scripts/export_now_playing.py` (remove ffprobe)
- [ ] Update systemd service for cleanup cron

### Phase 4: Batch Ingestion
- [ ] Fix `scripts/batch_ingest_assets.py` (already drafted)
- [ ] Test batch ingestion with existing bumpers/breaks
- [ ] Run batch ingestion on production bumpers/breaks

### Phase 5: Testing & Validation
- [ ] Run unit tests
- [ ] Run integration tests with production data copy
- [ ] Run migration on staging environment
- [ ] Perform manual testing checklist
- [ ] Run performance benchmarks
- [ ] Document results

### Phase 6: Production Deployment
- [ ] Backup production database
- [ ] Run migration script on production
- [ ] Add foreign key constraint
- [ ] Add play_history.played_at index
- [ ] Deploy updated scripts
- [ ] Monitor for 48 hours
- [ ] Verify cleanup script runs successfully

---

## Success Criteria

- ✅ All bumpers and breaks ingested into assets table with SHA256 IDs
- ✅ All play_history records migrated to SHA256 IDs (zero orphans)
- ✅ Foreign key constraint added and satisfied
- ✅ export_now_playing.py executes in <10ms (40x faster)
- ✅ No ffprobe calls remaining in codebase
- ✅ New breaks auto-ingest after generation
- ✅ Old breaks automatically cleaned up after 48 hours
- ✅ Station ID selection includes anti-repeat logic
- ✅ Frontend displays correct metadata within 2s for all track types
- ✅ All tests passing

---

## Future Enhancements

- Add Liquidsoap queue management to avoid repeating tracks within configurable window
- Implement Server-Sent Events for real-time frontend updates (eliminate 2s polling)
- Add prometheus metrics for ingestion success/failure rates
- Create admin UI for managing assets (upload, ingest, delete)
- Add support for additional asset types (promos, jingles, etc.)
