# Unified Asset Ingestion - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use @superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate to unified SHA256-based asset ingestion eliminating runtime ffprobe calls and enabling content-addressable storage.

**Architecture:** Single assets table with content-based deduplication (SHA256). All content types (music, bumpers, breaks) use same ingestion pipeline. Migration converts filename-stem IDs to SHA256 hashes with orphan handling for deleted files.

**Tech Stack:** Python 3.12, SQLite, ffmpeg-normalize, pytest

**Design Doc:** See `docs/plans/2025-12-28-unified-asset-ingestion-design.md` for complete architecture

---

## Phase 1: Database Schema & Core Functions

### Task 1: Run Schema Migration

**Files:**
- Run: `migrations/001_add_bumper_kind.sql`
- Database: `~/.config/ai_radio/radio.db`

**Step 1: Backup database**

```bash
cp ~/.config/ai_radio/radio.db ~/.config/ai_radio/radio.db.bak-$(date +%Y%m%d-%H%M%S)
```

Expected: Backup file created with timestamp

**Step 2: Run migration**

```bash
sqlite3 ~/.config/ai_radio/radio.db < migrations/001_add_bumper_kind.sql
```

Expected: No output (success)

**Step 3: Verify schema change**

```bash
sqlite3 ~/.config/ai_radio/radio.db "SELECT sql FROM sqlite_master WHERE name='assets';"
```

Expected: Output contains `CHECK(kind IN ('music', 'break', 'bed', 'safety', 'bumper'))`

**Step 4: Commit**

```bash
git add migrations/001_add_bumper_kind.sql
git commit -m "chore: run schema migration adding bumper kind"
```

---

### Task 2: Add get_asset_by_id() Helper

**Files:**
- Modify: `src/ai_radio/db_assets.py:72-108`
- Test: `tests/test_db_assets.py:33-38`

**Note:** Function `get_asset()` already exists and does this. This task creates an alias for clarity.

**Step 1: Add alias in db_assets.py**

After line 108, add:

```python


# Alias for clarity in migration code
get_asset_by_id = get_asset
```

**Step 2: Verify existing tests pass**

```bash
uv run pytest tests/test_db_assets.py::test_get_asset_by_id -v
```

Expected: PASSED (test already exists)

**Step 3: Commit**

```bash
git add src/ai_radio/db_assets.py
git commit -m "refactor: add get_asset_by_id alias for clarity"
```

---

### Task 3: Add measure_loudness() Function

**Files:**
- Create: Tests first
- Modify: `src/ai_radio/audio.py` (after normalize_audio function)

**Step 1: Write failing test**

Add to `tests/test_audio.py`:

```python
def test_measure_loudness_returns_stats(tmp_path):
    """Verify measure_loudness returns loudness stats without creating output."""
    from ai_radio.audio import measure_loudness

    # Use existing test track
    test_track = Path("tests/fixtures/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    result = measure_loudness(test_track)

    assert "loudness_lufs" in result
    assert "true_peak_dbtp" in result
    assert isinstance(result["loudness_lufs"], float)
    assert isinstance(result["true_peak_dbtp"], float)
    assert result["loudness_lufs"] < 0  # LUFS is typically negative


def test_measure_loudness_nonexistent_file():
    """Verify measure_loudness raises ValueError for missing file."""
    from ai_radio.audio import measure_loudness

    with pytest.raises(ValueError, match="File not found"):
        measure_loudness(Path("/nonexistent/file.mp3"))


def test_measure_loudness_invalid_audio(tmp_path):
    """Verify measure_loudness raises ValueError for invalid audio."""
    from ai_radio.audio import measure_loudness

    invalid_file = tmp_path / "invalid.mp3"
    invalid_file.write_text("not an audio file")

    with pytest.raises(ValueError, match="Failed to measure loudness"):
        measure_loudness(invalid_file)
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_audio.py::test_measure_loudness_returns_stats -v
uv run pytest tests/test_audio.py::test_measure_loudness_nonexistent_file -v
uv run pytest tests/test_audio.py::test_measure_loudness_invalid_audio -v
```

Expected: All FAIL with "ImportError: cannot import name 'measure_loudness'"

**Step 3: Implement measure_loudness()**

Add to `src/ai_radio/audio.py` after the `normalize_audio` function:

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
    if not input_path.exists():
        raise ValueError(f"File not found: {input_path}")

    try:
        cmd = [
            "ffmpeg-normalize",
            str(input_path),
            "-n",  # No-op / dry-run mode
            "-f",  # Force overwrite
            "--normalization-type", "ebu",
            "--print-stats",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

        # Parse output for loudness stats
        # Example line: "Integrated loudness: -23.5 LUFS"
        # Example line: "True peak: -1.2 dBTP"
        loudness_lufs = None
        true_peak_dbtp = None

        for line in result.stderr.splitlines():
            if "Input Integrated" in line or "Integrated loudness" in line:
                # Extract number before "LUFS"
                match = re.search(r"(-?\d+\.?\d*)\s*LUFS", line)
                if match:
                    loudness_lufs = float(match.group(1))
            elif "Input True Peak" in line or "True peak" in line:
                # Extract number before "dBTP"
                match = re.search(r"(-?\d+\.?\d*)\s*dBTP", line)
                if match:
                    true_peak_dbtp = float(match.group(1))

        if loudness_lufs is None or true_peak_dbtp is None:
            raise ValueError(
                f"Failed to parse loudness stats from ffmpeg-normalize output"
            )

        return {
            "loudness_lufs": loudness_lufs,
            "true_peak_dbtp": true_peak_dbtp,
        }

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to measure loudness: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise ValueError(f"Loudness measurement timed out for {input_path}")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_audio.py::test_measure_loudness_returns_stats -v
uv run pytest tests/test_audio.py::test_measure_loudness_nonexistent_file -v
uv run pytest tests/test_audio.py::test_measure_loudness_invalid_audio -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/ai_radio/audio.py tests/test_audio.py
git commit -m "feat: add measure_loudness() for read-only audio analysis"
```

---

### Task 4: Fix Deduplication Bug in ingest_audio_file()

**Files:**
- Modify: `src/ai_radio/ingest.py:68-73`
- Test: `tests/test_ingest.py`

**Step 1: Write failing test for correct behavior**

Add to `tests/test_ingest.py`:

```python
def test_ingest_deduplication_by_content(tmp_path):
    """Verify deduplication checks SHA256, not file path."""
    import shutil
    from ai_radio.ingest import ingest_audio_file

    # Skip if test track not available
    test_track = Path("tests/fixtures/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    # Create two copies with different names
    file1 = tmp_path / "copy1.mp3"
    file2 = tmp_path / "copy2.mp3"
    shutil.copy(test_track, file1)
    shutil.copy(test_track, file2)

    # Set up database and output directory
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create minimal database
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER,
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # Ingest first file
    result1 = ingest_audio_file(
        source_path=file1,
        kind="music",
        db_path=db_path,
        music_dir=output_dir,
    )

    # Ingest second file (same content, different path)
    result2 = ingest_audio_file(
        source_path=file2,
        kind="music",
        db_path=db_path,
        music_dir=output_dir,
    )

    # Should return same asset (deduplication by content)
    assert result1["id"] == result2["id"], "Same content should have same SHA256 ID"
    assert result1 == result2, "Should return existing record, not create duplicate"
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_ingest.py::test_ingest_deduplication_by_content -v
```

Expected: FAIL (current code checks by path, not SHA256)

**Step 3: Fix deduplication in ingest_audio_file()**

In `src/ai_radio/ingest.py`, replace lines 68-73:

```python
    try:
        # Extract metadata first to get SHA256
        print(f"📋 Extracting metadata from {source_path.name}...")
        metadata = extract_metadata(source_path)
        asset_id = metadata.sha256_id

        # Check if content already ingested (by SHA256, not path)
        from ai_radio.db_assets import get_asset_by_id
        existing = get_asset_by_id(conn, asset_id)
        if existing:
            print(f"⚠️  File content already ingested (SHA256: {asset_id[:16]}...)")
            print(f"   Existing path: {existing['path']}")
            return existing
```

And update line 75-80 to remove duplicate metadata extraction:

```python
        # Metadata already extracted above for deduplication check
        print(f"   Title: {metadata.title}")
        print(f"   Artist: {metadata.artist}")
        print(f"   Duration: {metadata.duration_sec:.1f}s")

        # Step 2: Normalize audio
        # asset_id already computed above
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_ingest.py::test_ingest_deduplication_by_content -v
```

Expected: PASS

**Step 5: Run all ingest tests**

```bash
uv run pytest tests/test_ingest.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add src/ai_radio/ingest.py tests/test_ingest.py
git commit -m "fix: check SHA256 deduplication before path check

Fixes bug where duplicate content with different filenames
would be ingested multiple times. Now checks content hash
first for true content-addressable storage."
```

---

### Task 5: Add ingest_existing Parameter

**Files:**
- Modify: `src/ai_radio/ingest.py:21-28,63-62`
- Test: `tests/test_ingest.py`

**Step 1: Write failing tests**

Add to `tests/test_ingest.py`:

```python
def test_ingest_existing_registers_without_normalization(tmp_path):
    """Verify ingest_existing=True skips normalization."""
    import shutil
    from ai_radio.ingest import ingest_audio_file

    test_track = Path("tests/fixtures/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    # Copy to temp location
    source_file = tmp_path / "existing.mp3"
    shutil.copy(test_track, source_file)

    # Set up database
    db_path = tmp_path / "test.db"
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety', 'bumper')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER,
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    # Ingest with ingest_existing=True
    result = ingest_audio_file(
        source_path=source_file,
        kind="bumper",
        db_path=db_path,
        ingest_existing=True,
    )

    # Should use source path as-is
    assert result["path"] == str(source_file)
    assert result["kind"] == "bumper"
    assert result["loudness_lufs"] is not None  # Still measured
    assert result["duration_sec"] > 0


def test_ingest_existing_requires_no_output_dir():
    """Verify ingest_existing=True doesn't require output_dir."""
    from ai_radio.ingest import ingest_audio_file

    # This should NOT raise even though output_dir not provided
    # (Will fail at file exists check, but signature should work)
    try:
        ingest_audio_file(
            source_path=Path("/nonexistent.mp3"),
            kind="bumper",
            db_path=Path("/tmp/test.db"),
            ingest_existing=True,
        )
    except ValueError as e:
        # Should fail on file not found, not missing output_dir
        assert "not found" in str(e).lower()
        assert "output_dir" not in str(e).lower()


def test_ingest_new_requires_output_dir():
    """Verify ingest_existing=False requires output_dir."""
    from ai_radio.ingest import ingest_audio_file

    with pytest.raises(ValueError, match="output_dir.*required"):
        ingest_audio_file(
            source_path=Path("/nonexistent.mp3"),
            kind="music",
            db_path=Path("/tmp/test.db"),
            ingest_existing=False,
        )
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_ingest.py::test_ingest_existing_registers_without_normalization -v
uv run pytest tests/test_ingest.py::test_ingest_existing_requires_no_output_dir -v
uv run pytest tests/test_ingest.py::test_ingest_new_requires_output_dir -v
```

Expected: All FAIL (ingest_existing parameter doesn't exist yet)

**Step 3: Update function signature**

In `src/ai_radio/ingest.py`, replace lines 21-28:

```python
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
        source_path: Path to source audio file
        kind: Asset kind (music, break, bed, safety, bumper)
        db_path: Path to SQLite database
        output_dir: Output directory for normalized files (required when ingest_existing=False)
        target_lufs: Target loudness in LUFS
        true_peak: True peak limit in dBTP
        ingest_existing: If True, register existing file in-place without normalization

    Returns:
        dict with asset information

    Raises:
        ValueError: If ingestion fails or required parameters missing
    """
```

**Step 4: Add validation at start of function**

After line 45, add:

```python
    # Validate parameters
    if not ingest_existing and output_dir is None:
        raise ValueError("output_dir is required when ingest_existing=False")
```

**Step 5: Update directory validation**

Replace lines 51-62 with:

```python
    # Validate output directory only for new ingestion
    if not ingest_existing:
        if not output_dir.exists():
            raise ValueError(f"Output directory does not exist: {output_dir}")
        if not output_dir.is_dir():
            raise ValueError(f"Output directory path is not a directory: {output_dir}")
        # Test write permission
        test_file = output_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError) as e:
            raise ValueError(f"Output directory is not writable: {output_dir}") from e
```

**Step 6: Add branching logic for ingest_existing**

After the deduplication check (around line 85), replace normalization section with:

```python
        print(f"   Title: {metadata.title}")
        print(f"   Artist: {metadata.artist}")
        print(f"   Duration: {metadata.duration_sec:.1f}s")

        if ingest_existing:
            # Register existing file without normalization
            print(f"📍 Registering existing file (no normalization)...")
            from ai_radio.audio import measure_loudness

            loudness_stats = measure_loudness(source_path)
            print(f"   Loudness: {loudness_stats['loudness_lufs']:.1f} LUFS")
            print(f"   True Peak: {loudness_stats['true_peak_dbtp']:.1f} dBTP")

            # Use source path as-is
            final_path = source_path
            loudness_lufs = loudness_stats["loudness_lufs"]
            true_peak_dbtp = loudness_stats["true_peak_dbtp"]
        else:
            # Normalize and copy to output directory
            output_path = output_dir / f"{asset_id}.mp3"

            print(f"🔊 Normalizing audio to {target_lufs} LUFS...")
            norm_result = normalize_audio(
                source_path,
                output_path,
                target_lufs=target_lufs,
                true_peak=true_peak,
            )
            print(f"   Loudness: {norm_result['loudness_lufs']:.1f} LUFS")
            print(f"   True Peak: {norm_result['true_peak_dbtp']:.1f} dBTP")

            final_path = output_path
            loudness_lufs = norm_result["loudness_lufs"]
            true_peak_dbtp = norm_result["true_peak_dbtp"]

        # Step 3: Insert into database
        print(f"💾 Inserting asset record into database...")
        try:
            insert_asset(
                conn,
                asset_id=asset_id,
                path=final_path,
                kind=kind,
                duration_sec=metadata.duration_sec,
                loudness_lufs=loudness_lufs,
                true_peak_dbtp=true_peak_dbtp,
                title=metadata.title,
                artist=metadata.artist,
                album=metadata.album,
            )
```

**Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/test_ingest.py::test_ingest_existing_registers_without_normalization -v
uv run pytest tests/test_ingest.py::test_ingest_existing_requires_no_output_dir -v
uv run pytest tests/test_ingest.py::test_ingest_new_requires_output_dir -v
```

Expected: All PASS

**Step 8: Run all ingest tests**

```bash
uv run pytest tests/test_ingest.py -v
```

Expected: All PASS

**Step 9: Commit**

```bash
git add src/ai_radio/ingest.py tests/test_ingest.py
git commit -m "feat: add ingest_existing parameter for registering normalized files

Enables ingestion of pre-normalized bumpers and breaks without
transcoding. Measures loudness without creating output file.
Renames music_dir to output_dir for clarity."
```

---

## Phase 2: Migration Script

### Task 6: Create Migration Script Structure

**Files:**
- Create: `scripts/migrate_to_sha256_ids.py`

**Step 1: Create script skeleton**

```python
#!/usr/bin/env python3
"""Migrate play_history records from filename stems to SHA256 IDs.

This script:
1. Scans bumpers/ and breaks/ directories for audio files
2. Computes SHA256 hash for each file
3. Ingests files into assets table
4. Builds mapping: filename_stem → SHA256
5. Updates play_history with SHA256 IDs
6. Handles orphans (deleted files) with synthetic records

Usage:
    ./scripts/migrate_to_sha256_ids.py [--dry-run] [--db-path PATH]

Exit codes:
    0: Success
    1: Error occurred
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config
from ai_radio.ingest import ingest_audio_file
from ai_radio.audio import extract_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def scan_and_hash_files(directory: Path, kind: str) -> Dict[str, Tuple[str, Path]]:
    """Scan directory and build filename_stem → (SHA256, path) mapping.

    Args:
        directory: Directory to scan
        kind: Asset kind (bumper/break)

    Returns:
        dict mapping filename_stem to (sha256_hash, file_path)
    """
    mapping = {}

    for ext in [".mp3", ".wav", ".ogg"]:
        for file_path in directory.glob(f"*{ext}"):
            stem = file_path.stem

            # Compute SHA256
            logger.info(f"Computing SHA256 for {file_path.name}...")
            metadata = extract_metadata(file_path)
            sha256 = metadata.sha256_id

            mapping[stem] = (sha256, file_path)
            logger.info(f"  {stem} → {sha256[:16]}...")

    return mapping


def find_non_sha256_ids(conn: sqlite3.Connection) -> List[str]:
    """Find all play_history asset_ids that aren't SHA256 hashes.

    Args:
        conn: Database connection

    Returns:
        List of non-SHA256 asset_ids
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT asset_id
        FROM play_history
        WHERE length(asset_id) != 64
    """)

    return [row[0] for row in cursor.fetchall()]


def create_orphan_asset(
    conn: sqlite3.Connection,
    filename_stem: str,
    kind: str,
) -> str:
    """Create synthetic asset record for deleted file.

    Args:
        conn: Database connection
        filename_stem: Original filename stem
        kind: Asset kind (bumper/break)

    Returns:
        Generated orphan asset_id
    """
    from ai_radio.db_assets import insert_asset

    orphan_id = f"orphan_{filename_stem}"

    logger.warning(f"Creating orphan record for deleted file: {filename_stem}")

    insert_asset(
        conn,
        asset_id=orphan_id,
        path=Path(f"/dev/null/deleted/{filename_stem}"),
        kind=kind,
        duration_sec=0.0,
        title=f"[Deleted Asset] {filename_stem}",
        artist="Unknown",
    )

    return orphan_id


def migrate_play_history(
    conn: sqlite3.Connection,
    mapping: Dict[str, str],
    dry_run: bool = False,
) -> int:
    """Update play_history with SHA256 IDs.

    Args:
        conn: Database connection
        mapping: filename_stem → sha256_id mapping
        dry_run: If True, only show what would be updated

    Returns:
        Number of records updated
    """
    if not mapping:
        logger.info("No mappings to apply")
        return 0

    cursor = conn.cursor()

    # Build CASE expression
    case_parts = []
    for stem, sha256 in mapping.items():
        case_parts.append(f"WHEN '{stem}' THEN '{sha256}'")

    case_expr = "\n        ".join(case_parts)
    stems_list = ", ".join(f"'{stem}'" for stem in mapping.keys())

    query = f"""
        UPDATE play_history
        SET asset_id = CASE asset_id
        {case_expr}
        ELSE asset_id
        END
        WHERE asset_id IN ({stems_list})
    """

    if dry_run:
        logger.info(f"[DRY RUN] Would update {len(mapping)} distinct asset_ids")
        # Count how many records would be affected
        cursor.execute(f"SELECT COUNT(*) FROM play_history WHERE asset_id IN ({stems_list})")
        count = cursor.fetchone()[0]
        logger.info(f"[DRY RUN] Would affect {count} play_history records")
        return count

    cursor.execute(query)
    affected = cursor.rowcount
    conn.commit()

    logger.info(f"Updated {affected} play_history records")
    return affected


def main():
    """Entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate play_history to SHA256-based asset IDs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=config.db_path,
        help="Path to database (default: config.db_path)",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    # Backup database
    if not args.dry_run:
        backup_path = args.db_path.parent / f"{args.db_path.stem}.bak-pre-migration"
        logger.info(f"📦 Creating backup: {backup_path}")
        import shutil
        shutil.copy(args.db_path, backup_path)

    # Connect to database
    conn = sqlite3.connect(args.db_path)

    try:
        # Find non-SHA256 IDs
        logger.info("🔍 Finding non-SHA256 asset_ids in play_history...")
        non_sha256_ids = find_non_sha256_ids(conn)
        logger.info(f"Found {len(non_sha256_ids)} unique non-SHA256 IDs")

        if not non_sha256_ids:
            logger.info("✅ No migration needed - all IDs are already SHA256")
            return 0

        # Scan and hash files
        logger.info("=" * 60)
        logger.info("SCANNING BUMPERS")
        logger.info("=" * 60)
        bumper_mapping = scan_and_hash_files(config.bumpers_path, "bumper")

        logger.info("=" * 60)
        logger.info("SCANNING BREAKS")
        logger.info("=" * 60)
        break_mapping = scan_and_hash_files(config.breaks_path, "break")

        # Ingest files
        if not args.dry_run:
            logger.info("=" * 60)
            logger.info("INGESTING FILES")
            logger.info("=" * 60)

            for stem, (sha256, path) in bumper_mapping.items():
                ingest_audio_file(
                    source_path=path,
                    kind="bumper",
                    db_path=args.db_path,
                    ingest_existing=True,
                )

            for stem, (sha256, path) in break_mapping.items():
                ingest_audio_file(
                    source_path=path,
                    kind="break",
                    db_path=args.db_path,
                    ingest_existing=True,
                )

        # Build migration mapping (stem → SHA256 only)
        migration_mapping = {}
        for stem, (sha256, _) in bumper_mapping.items():
            migration_mapping[stem] = sha256
        for stem, (sha256, _) in break_mapping.items():
            migration_mapping[stem] = sha256

        # Handle orphans
        for asset_id in non_sha256_ids:
            if asset_id not in migration_mapping:
                logger.warning(f"Orphan detected: {asset_id} (file not found)")
                if not args.dry_run:
                    # Guess kind from filename
                    kind = "bumper" if "station_id" in asset_id else "break"
                    orphan_id = create_orphan_asset(conn, asset_id, kind)
                    migration_mapping[asset_id] = orphan_id

        # Migrate play_history
        logger.info("=" * 60)
        logger.info("MIGRATING PLAY_HISTORY")
        logger.info("=" * 60)
        affected = migrate_play_history(conn, migration_mapping, args.dry_run)

        # Save mapping log
        if not args.dry_run:
            mapping_file = args.db_path.parent / "migration_mapping.json"
            logger.info(f"📝 Writing mapping log: {mapping_file}")
            with open(mapping_file, "w") as f:
                json.dump(migration_mapping, f, indent=2)

        # Validation
        logger.info("=" * 60)
        logger.info("VALIDATION")
        logger.info("=" * 60)

        cursor = conn.cursor()

        # Check for orphans (should be 0 after migration)
        cursor.execute("""
            SELECT count(*) FROM play_history ph
            LEFT JOIN assets a ON ph.asset_id = a.id
            WHERE a.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]

        if orphan_count > 0:
            logger.error(f"❌ Found {orphan_count} orphaned play_history records!")
            return 1

        logger.info("✅ No orphaned play_history records")

        # Check for remaining non-SHA256 IDs
        cursor.execute("""
            SELECT count(*) FROM play_history
            WHERE length(asset_id) != 64 AND asset_id NOT LIKE 'orphan_%'
        """)
        remaining = cursor.fetchone()[0]

        if remaining > 0:
            logger.error(f"❌ Found {remaining} non-SHA256 IDs still in play_history!")
            return 1

        logger.info("✅ All play_history records migrated to SHA256")

        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Migrated {affected} play_history records")
        logger.info(f"✅ Ingested {len(bumper_mapping)} bumpers")
        logger.info(f"✅ Ingested {len(break_mapping)} breaks")

        if args.dry_run:
            logger.info("🔍 This was a dry run - no changes were made")

        return 0

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        conn.rollback()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make executable**

```bash
chmod +x scripts/migrate_to_sha256_ids.py
```

**Step 3: Test dry-run mode**

```bash
./scripts/migrate_to_sha256_ids.py --dry-run
```

Expected: Shows analysis without making changes

**Step 4: Commit**

```bash
git add scripts/migrate_to_sha256_ids.py
git commit -m "feat: add migration script for SHA256-based asset IDs

Migrates play_history from filename stems to SHA256 hashes.
Includes dry-run mode, orphan handling, and validation."
```

---

## Phase 3: Script Updates

### Task 7: Update record_play.py

**Files:**
- Modify: `scripts/record_play.py`
- Test: Manual testing (no unit tests for scripts)

**Step 1: Read current record_play.py**

```bash
cat scripts/record_play.py
```

**Step 2: Update to look up SHA256 from path**

Replace the section that writes to play_history with:

```python
# Look up asset by path to get SHA256 ID
conn = sqlite3.connect(config.db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, kind FROM assets WHERE path = ?", (file_path,))
row = cursor.fetchone()

if not row:
    logger.error(f"Asset not found in database: {file_path}")
    logger.error("Make sure all assets are ingested before playback")
    conn.close()
    return 1

asset_id, asset_kind = row

# Write to play_history with SHA256 ID
cursor.execute(
    "INSERT INTO play_history (asset_id, source, played_at) VALUES (?, ?, ?)",
    (asset_id, asset_kind, datetime.now(timezone.utc).isoformat())
)
conn.commit()
conn.close()

logger.info(f"Recorded play: {asset_id[:16]}... (kind={asset_kind})")
```

**Step 3: Commit**

```bash
git add scripts/record_play.py
git commit -m "feat: record plays with SHA256 asset IDs

Looks up asset by path to get SHA256 ID and kind.
Fails loudly if asset not in database."
```

---

### Task 8: Update enqueue_station_id.py

**Files:**
- Modify: `scripts/enqueue_station_id.py`

**Step 1: Replace filesystem scan with database query**

Replace the station ID selection logic with:

```python
import sqlite3
import random
from ai_radio.config import config

# Query database for station IDs (with anti-repeat logic)
conn = sqlite3.connect(config.db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT id, path FROM assets
    WHERE kind = 'bumper'
    AND id NOT IN (
        SELECT asset_id FROM play_history
        WHERE played_at > datetime('now', '-1 hour')
    )
""")

all_station_ids = cursor.fetchall()
conn.close()

if not all_station_ids:
    logger.warning("No station IDs available (all played within 1 hour)")
    # Fall back to any station ID
    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, path FROM assets WHERE kind = 'bumper'")
    all_station_ids = cursor.fetchall()
    conn.close()

if not all_station_ids:
    logger.error("No station IDs found in database")
    return 1

# Select random station ID
selected_id, selected_path = random.choice(all_station_ids)
logger.info(f"Selected station ID: {selected_id[:16]}...")
logger.info(f"Path: {selected_path}")

# Enqueue in Liquidsoap (use path)
# ... rest of enqueue logic using selected_path
```

**Step 2: Commit**

```bash
git add scripts/enqueue_station_id.py
git commit -m "feat: select station IDs from database with anti-repeat

Queries assets table instead of scanning filesystem.
Includes 1-hour anti-repeat window."
```

---

### Task 9: Simplify export_now_playing.py

**Files:**
- Modify: `scripts/export_now_playing.py`

**Step 1: Replace complex query logic**

Replace the get_current_playing() function with simplified version:

```python
def get_current_playing() -> tuple[dict | None, dict | None]:
    """Get current track from play_history + assets JOIN."""
    from datetime import datetime, timezone, timedelta

    conn = sqlite3.connect(config.db_path)
    cursor = conn.cursor()

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
    conn.close()

    if not row:
        return None, None

    # Graceful degradation for deleted assets
    if row[1] is None:  # title is NULL = deleted asset
        current = {
            "asset_id": row[0],
            "title": "[Deleted Track]",
            "artist": "Unknown",
            "album": None,
            "duration_sec": 0,
            "played_at": row[5],
            "source": "unknown"
        }
    else:
        current = {
            "asset_id": row[0],
            "title": row[1],
            "artist": row[2],
            "album": row[3],
            "duration_sec": row[4],
            "played_at": row[5],
            "source": row[6]
        }

    # Stream info from Icecast (keep existing logic)
    stream_info = get_stream_info()

    return current, stream_info
```

**Step 2: Remove all ffprobe calls and path construction**

Search for and remove:
- `get_duration_from_file()` calls
- File path construction from asset_id
- Extension guessing loops
- Sleep buffers

**Step 3: Run export script to verify**

```bash
./scripts/export_now_playing.py
cat /srv/ai_radio/public/now_playing.json | jq .
```

Expected: Valid JSON with current track info (no errors)

**Step 4: Commit**

```bash
git add scripts/export_now_playing.py
git commit -m "refactor: simplify export with direct assets JOIN

Eliminates all ffprobe calls and path construction.
Simple LEFT JOIN for resilience to deleted assets.
~50 lines down from ~150."
```

---

### Task 10: Create cleanup_old_breaks.py

**Files:**
- Create: `scripts/cleanup_old_breaks.py`

**Step 1: Create cleanup script**

```python
#!/usr/bin/env python3
"""Cleanup breaks older than 48 hours.

Removes break assets and files that are older than 48 hours.
Designed to run daily via cron.

Usage:
    ./scripts/cleanup_old_breaks.py [--dry-run] [--age-hours HOURS]

Exit codes:
    0: Success
    1: Error occurred
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_old_breaks(
    db_path: Path,
    age_hours: int = 48,
    dry_run: bool = False,
) -> int:
    """Delete break assets older than specified age.

    Args:
        db_path: Path to database
        age_hours: Age threshold in hours
        dry_run: If True, only show what would be deleted

    Returns:
        Number of breaks deleted
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Find old breaks (portable SQL - no RETURNING)
        cursor.execute(
            """
            SELECT id, path, created_at FROM assets
            WHERE kind = 'break'
            AND created_at < datetime('now', ?)
            """,
            (f"-{age_hours} hours",)
        )

        old_breaks = cursor.fetchall()

        if not old_breaks:
            logger.info("No old breaks to clean up")
            return 0

        logger.info(f"Found {len(old_breaks)} breaks older than {age_hours} hours")

        if dry_run:
            for break_id, path, created_at in old_breaks:
                logger.info(f"[DRY RUN] Would delete: {path} (created {created_at})")
            return len(old_breaks)

        # Delete from database
        break_ids = [b[0] for b in old_breaks]
        placeholders = ','.join('?' for _ in break_ids)
        cursor.execute(f"DELETE FROM assets WHERE id IN ({placeholders})", break_ids)
        conn.commit()

        logger.info(f"Deleted {len(break_ids)} records from database")

        # Delete files from disk
        deleted_count = 0
        for break_id, path, created_at in old_breaks:
            file_path = Path(path)
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"✅ Deleted: {path}")
                    deleted_count += 1
                else:
                    logger.warning(f"⚠️  File already gone: {path}")
            except OSError as e:
                logger.error(f"❌ Error deleting {path}: {e}")

        logger.info(f"Successfully deleted {deleted_count} files")
        return deleted_count

    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        conn.rollback()
        raise

    finally:
        conn.close()


def main():
    """Entry point for cleanup script."""
    parser = argparse.ArgumentParser(
        description="Cleanup breaks older than specified age"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes",
    )
    parser.add_argument(
        "--age-hours",
        type=int,
        default=48,
        help="Age threshold in hours (default: 48)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=config.db_path,
        help="Path to database (default: config.db_path)",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")

    try:
        deleted = cleanup_old_breaks(
            db_path=args.db_path,
            age_hours=args.age_hours,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            logger.info(f"🔍 Would delete {deleted} breaks")
        else:
            logger.info(f"✅ Cleaned up {deleted} old breaks")

        return 0

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Make executable**

```bash
chmod +x scripts/cleanup_old_breaks.py
```

**Step 3: Test dry-run**

```bash
./scripts/cleanup_old_breaks.py --dry-run
```

Expected: Shows what would be deleted (probably nothing)

**Step 4: Commit**

```bash
git add scripts/cleanup_old_breaks.py
git commit -m "feat: add cleanup script for old breaks

Deletes break assets and files older than 48 hours.
Includes dry-run mode and portable SQL."
```

---

### Task 11: Update generate_break.py for Auto-Ingest

**Files:**
- Modify: `scripts/generate_break.py`

**Step 1: Add auto-ingest after generation**

After the break file is generated, add:

```python
# Auto-ingest break immediately
try:
    from ai_radio.ingest import ingest_audio_file

    logger.info("📥 Auto-ingesting break into assets table...")
    ingest_audio_file(
        source_path=break_path,
        kind="break",
        db_path=config.db_path,
        ingest_existing=True,
    )
    logger.info("✅ Break ingested successfully")
except Exception as e:
    logger.error(f"❌ Failed to ingest break: {e}")
    return 1  # Fail loudly for systemd alerting
```

**Step 2: Commit**

```bash
git add scripts/generate_break.py
git commit -m "feat: auto-ingest breaks after generation

Ensures all breaks are in assets table before playback.
Ingestion failure causes script to fail for alerting."
```

---

## Phase 4: Testing & Validation

### Task 12: Run All Unit Tests

**Step 1: Run complete test suite**

```bash
uv run pytest -v
```

Expected: All tests PASS

**Step 2: Check test coverage**

```bash
uv run pytest --cov=src/ai_radio --cov-report=term-missing
```

Expected: High coverage (>80%) on modified modules

**Step 3: Commit any test fixes**

```bash
git add tests/
git commit -m "test: ensure all tests pass after refactoring"
```

---

### Task 13: Integration Test - Full Migration

**Step 1: Copy production database**

```bash
scp ai-radio:~/.config/ai_radio/radio.db /tmp/radio-test.db
```

**Step 2: Run migration on test database**

```bash
./scripts/migrate_to_sha256_ids.py --db-path /tmp/radio-test.db
```

Expected: Migration completes successfully

**Step 3: Validate results**

```bash
sqlite3 /tmp/radio-test.db "
  SELECT count(*) FROM play_history ph
  LEFT JOIN assets a ON ph.asset_id = a.id
  WHERE a.id IS NULL;
"
```

Expected: 0 (no orphans)

```bash
sqlite3 /tmp/radio-test.db "
  SELECT count(*) FROM play_history
  WHERE length(asset_id) != 64 AND asset_id NOT LIKE 'orphan_%';
"
```

Expected: 0 (all migrated)

**Step 4: Document results**

Create notes about any issues encountered.

---

## Phase 5: Production Deployment

### Task 14: Deploy to Production

**Step 1: Stop radio services**

```bash
ssh ai-radio 'systemctl stop ai-radio-liquidsoap ai-radio-export-nowplaying'
```

**Step 2: Deploy code**

```bash
./deploy.sh
```

**Step 3: Run migration**

```bash
ssh ai-radio 'cd /srv/ai_radio && ./scripts/migrate_to_sha256_ids.py'
```

Expected: Migration succeeds

**Step 4: Add database constraints**

```bash
ssh ai-radio 'sqlite3 ~/.config/ai_radio/radio.db' <<'EOF'
-- Add performance index
CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);

-- Add foreign key constraint
-- Note: SQLite requires PRAGMA foreign_keys=ON and table recreation for FK
-- This is complex - recommend separate migration script if needed
EOF
```

**Step 5: Restart services**

```bash
ssh ai-radio 'systemctl start ai-radio-liquidsoap ai-radio-export-nowplaying'
```

**Step 6: Monitor logs**

```bash
ssh ai-radio 'journalctl -u ai-radio-liquidsoap -f'
```

Watch for errors for 5 minutes.

**Step 7: Verify frontend**

Open https://radio.clintecker.com and verify:
- Current track shows correctly
- Progress bar works
- Station IDs display properly
- Transitions are smooth

---

## Phase 6: Cleanup & Documentation

### Task 15: Add Cleanup Cron Job

**Step 1: Create systemd timer**

Create `/etc/systemd/system/ai-radio-cleanup-breaks.timer`:

```ini
[Unit]
Description=Cleanup old breaks daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/ai-radio-cleanup-breaks.service`:

```ini
[Unit]
Description=Cleanup old breaks

[Service]
Type=oneshot
User=ai-radio
ExecStart=/srv/ai_radio/scripts/cleanup_old_breaks.py
StandardOutput=journal
StandardError=journal
```

**Step 2: Enable timer**

```bash
ssh ai-radio 'sudo systemctl daemon-reload'
ssh ai-radio 'sudo systemctl enable ai-radio-cleanup-breaks.timer'
ssh ai-radio 'sudo systemctl start ai-radio-cleanup-breaks.timer'
```

**Step 3: Verify timer**

```bash
ssh ai-radio 'systemctl list-timers | grep cleanup'
```

Expected: Timer listed with next run time

---

### Task 16: Performance Benchmark

**Step 1: Benchmark export_now_playing.py**

```bash
ssh ai-radio 'time /srv/ai_radio/scripts/export_now_playing.py'
```

Record time (should be <10ms)

**Step 2: Document results**

Add to FIXES_APPLIED.md or create PERFORMANCE.md with:
- Before/after timing
- Query plan analysis
- Memory usage

---

### Task 17: Final Verification & Commit

**Step 1: Verify all checklist items**

Go through design doc checklist:
- ✅ Schema migration run
- ✅ All functions implemented
- ✅ Migration script tested
- ✅ Scripts updated
- ✅ Tests passing
- ✅ Production deployed
- ✅ Monitoring active

**Step 2: Update documentation**

Update FIXES_APPLIED.md with migration summary.

**Step 3: Final commit**

```bash
git add docs/
git commit -m "docs: update documentation for unified asset ingestion

Migration completed successfully. All assets now use SHA256 IDs.
Export script simplified from ~150 to ~50 lines.
Performance improvement: 40x faster (200ms → 5ms)."
```

**Step 4: Push to main**

```bash
git push origin feature/unified-asset-ingestion
```

**Step 5: Create PR or merge**

Follow standard process for merging feature branch.

---

## Rollback Plan

If issues occur:

```bash
# Stop services
ssh ai-radio 'systemctl stop ai-radio-*'

# Restore database
ssh ai-radio 'cp ~/.config/ai_radio/radio.db.bak-pre-migration ~/.config/ai_radio/radio.db'

# Revert code
git revert <commit-range>
./deploy.sh

# Restart services
ssh ai-radio 'systemctl start ai-radio-*'
```

---

## Success Criteria

- ✅ All bumpers and breaks in assets table with SHA256 IDs
- ✅ All play_history records migrated (zero orphans)
- ✅ Foreign key constraint satisfied
- ✅ export_now_playing.py <10ms execution time
- ✅ No ffprobe calls in codebase
- ✅ New breaks auto-ingest
- ✅ Cleanup script runs daily
- ✅ All tests passing
- ✅ Frontend displays correctly
- ✅ No errors in logs for 48 hours

---

## Notes

**DRY (Don't Repeat Yourself)**: Unified ingestion pipeline for all asset types

**YAGNI (You Aren't Gonna Need It)**: No speculative features. Migration handles exact current needs.

**TDD (Test-Driven Development)**: Every function has tests written first

**Frequent Commits**: Commit after each task (17 commits total)

**Reference Skills**:
- @superpowers:test-driven-development - Test writing guidance
- @superpowers:systematic-debugging - If issues arise
- @superpowers:verification-before-completion - Before claiming success
