# Phase 2: Asset Management - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ingest and normalize music library with complete metadata tracking

**Architecture:** Python script reads source music directory, normalizes audio using ffmpeg-normalize to broadcast standards (-18 LUFS, -1.0 dBTP), extracts metadata, generates SHA256 asset IDs, and populates SQLite database with atomic file operations.

**Tech Stack:** Python 3.11+, uv, ffmpeg-normalize, mutagen (metadata), SQLite

---

## Overview

This phase implements the music asset pipeline that:
1. Discovers music files from source directory
2. Extracts metadata (title, artist, album, duration)
3. Normalizes loudness to broadcast standard (-18 LUFS, -1.0 dBTP)
4. Generates unique SHA256 asset IDs
5. Stores normalized audio in `/srv/ai_radio/assets/music/`
6. Populates database with asset records

**Why This Matters:** The normalized music library is the foundation for the always-on stream. All tracks must meet loudness standards to ensure consistent listener experience.

---

## Task 1: Project Dependencies

**Files:**
- Modify: `/srv/ai_radio/pyproject.toml`

**Step 1: Add audio processing dependencies**

Run:
```bash
cd /srv/ai_radio
uv add mutagen ffmpeg-normalize
```

Expected: Dependencies added to pyproject.toml

**Step 2: Add development/testing dependencies**

Run:
```bash
uv add --dev pytest pytest-cov
```

Expected: Dev dependencies added

**Step 3: Verify ffmpeg is installed**

Run:
```bash
ffmpeg -version
ffmpeg-normalize --version
```

Expected: Both commands show version output

---

## Task 2: Database Schema Verification

**Files:**
- Verify: `/srv/ai_radio/db/schema.sql`

**Step 1: Verify assets table schema**

The schema should already exist from Phase 0. Verify it matches SOW requirements:

```sql
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,              -- SHA256 hash
    type TEXT NOT NULL,               -- 'music', 'break', 'bumper'
    path TEXT NOT NULL UNIQUE,        -- Absolute path to normalized file
    original_path TEXT,               -- Source file path
    title TEXT,                       -- Track title
    artist TEXT,                      -- Artist name
    album TEXT,                       -- Album name
    duration_seconds REAL NOT NULL,   -- Duration in seconds
    created_at TEXT NOT NULL,         -- ISO timestamp
    metadata TEXT                     -- JSON blob for extra data
);
```

Run:
```bash
sqlite3 /srv/ai_radio/data/radio.db ".schema assets"
```

Expected: Schema matches above

**Step 2: Create database index for type lookups**

Run:
```bash
sqlite3 /srv/ai_radio/data/radio.db "CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);"
```

Expected: Index created

---

## Task 3: Source Music Directory Setup

**Files:**
- Create: `/srv/ai_radio/assets/music/` (normalized output)
- Create: `/srv/ai_radio/assets/source_music/` (input)
- Create: `/srv/ai_radio/tmp/` (atomic operations)

**Step 1: Create directory structure**

Run:
```bash
sudo -u ai-radio mkdir -p /srv/ai_radio/assets/music
sudo -u ai-radio mkdir -p /srv/ai_radio/assets/source_music
sudo -u ai-radio mkdir -p /srv/ai_radio/tmp
```

Expected: Directories created with ai-radio ownership

**Step 2: Verify directory permissions**

Run:
```bash
ls -la /srv/ai_radio/assets/
```

Expected: All directories owned by ai-radio:ai-radio with 755 permissions

**Step 3: Add placeholder source music (for testing)**

For development/testing, create a test track:

Run:
```bash
# Create a 30-second sine wave test tone
ffmpeg -f lavfi -i "sine=frequency=440:duration=30" \
  -metadata title="Test Tone 440Hz" \
  -metadata artist="Test Artist" \
  -metadata album="Test Album" \
  /srv/ai_radio/assets/source_music/test_track.mp3

sudo chown ai-radio:ai-radio /srv/ai_radio/assets/source_music/test_track.mp3
```

Expected: Test MP3 file created

---

## Task 4: Audio Metadata Extraction Module

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/audio.py`

**Step 1: Create audio metadata extraction function**

Create file `/srv/ai_radio/src/ai_radio/audio.py`:
```python
"""Audio processing utilities for asset management."""

import hashlib
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.flac import FLAC


class AudioMetadata:
    """Extracted metadata from audio file."""

    def __init__(
        self,
        path: Path,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration_seconds: float = 0.0,
    ):
        self.path = path
        self.title = title or path.stem  # Fallback to filename
        self.artist = artist or "Unknown Artist"
        self.album = album or "Unknown Album"
        self.duration_seconds = duration_seconds

    @property
    def sha256_id(self) -> str:
        """Generate SHA256 hash of file contents for asset ID."""
        hasher = hashlib.sha256()
        with open(self.path, "rb") as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


def extract_metadata(file_path: Path) -> AudioMetadata:
    """Extract metadata from audio file using mutagen.

    Args:
        file_path: Path to audio file (MP3, FLAC, etc.)

    Returns:
        AudioMetadata instance with extracted information

    Raises:
        ValueError: If file cannot be read or is not a valid audio file
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")

        # Extract common tags (mutagen uses lists for tag values)
        title = None
        artist = None
        album = None

        if "title" in audio:
            title = str(audio["title"][0])
        if "artist" in audio:
            artist = str(audio["artist"][0])
        if "album" in audio:
            album = str(audio["album"][0])

        # Get duration
        duration = audio.info.length if audio.info else 0.0

        return AudioMetadata(
            path=file_path,
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration,
        )

    except Exception as e:
        raise ValueError(f"Failed to extract metadata from {file_path}: {e}")
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/audio.py << 'EOF'
[content above]
EOF
```

Expected: File created

**Step 2: Create test for metadata extraction**

Create file `/srv/ai_radio/tests/test_audio.py`:
```python
"""Tests for audio metadata extraction."""

import pytest
from pathlib import Path

from ai_radio.audio import extract_metadata, AudioMetadata


def test_extract_metadata_from_test_track():
    """Test metadata extraction from known test file."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    metadata = extract_metadata(test_file)

    assert metadata.title == "Test Tone 440Hz"
    assert metadata.artist == "Test Artist"
    assert metadata.album == "Test Album"
    assert metadata.duration_seconds > 0


def test_extract_metadata_nonexistent_file():
    """Test that nonexistent file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        extract_metadata(Path("/nonexistent/file.mp3"))


def test_sha256_id_generation():
    """Test SHA256 ID generation produces consistent hash."""
    test_file = Path("/srv/ai_radio/assets/source_music/test_track.mp3")

    if not test_file.exists():
        pytest.skip("Test track not available")

    metadata = extract_metadata(test_file)
    sha1 = metadata.sha256_id
    sha2 = metadata.sha256_id

    assert sha1 == sha2  # Deterministic
    assert len(sha1) == 64  # SHA256 is 64 hex characters
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/tests/test_audio.py << 'EOF'
[content above]
EOF
```

Expected: Test file created

**Step 3: Run tests to verify metadata extraction**

Run:
```bash
cd /srv/ai_radio
uv run pytest tests/test_audio.py -v
```

Expected: All tests pass

---

## Task 5: Audio Normalization Module

**Files:**
- Modify: `/srv/ai_radio/src/ai_radio/audio.py`

**Step 1: Add normalization function to audio.py**

Add to `/srv/ai_radio/src/ai_radio/audio.py`:
```python
import subprocess
import tempfile
from datetime import datetime


def normalize_audio(
    source_path: Path,
    output_path: Path,
    loudness_target: float = -18.0,
    true_peak: float = -1.0,
) -> Path:
    """Normalize audio file to broadcast loudness standards.

    Uses ffmpeg-normalize with EBU R128 loudness normalization.

    Args:
        source_path: Input audio file
        output_path: Destination for normalized file
        loudness_target: Target loudness in LUFS (default: -18.0)
        true_peak: True peak limit in dBTP (default: -1.0)

    Returns:
        Path to normalized output file

    Raises:
        RuntimeError: If normalization fails
    """
    if not source_path.exists():
        raise ValueError(f"Source file not found: {source_path}")

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use temp file for atomic write
    with tempfile.NamedTemporaryFile(
        suffix=".mp3",
        dir=output_path.parent,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Run ffmpeg-normalize
        cmd = [
            "ffmpeg-normalize",
            str(source_path),
            "-o", str(tmp_path),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            "-f",  # Force overwrite
            "-nt", "ebu",  # EBU R128 normalization
            "-t", str(loudness_target),  # Target loudness
            "-tp", str(true_peak),  # True peak
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg-normalize failed: {result.stderr}"
            )

        # Atomic move to final location
        tmp_path.rename(output_path)

        return output_path

    except Exception as e:
        # Clean up temp file on error
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(f"Normalization failed: {e}")
```

Run:
```bash
# Append to existing audio.py file
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/src/ai_radio/audio.py
[content above]
EOF
```

Expected: Function added to audio.py

**Step 2: Create test for normalization**

Add to `/srv/ai_radio/tests/test_audio.py`:
```python
from ai_radio.audio import normalize_audio


def test_normalize_audio():
    """Test audio normalization produces valid output."""
    source = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    output = Path("/srv/ai_radio/tmp/test_normalized.mp3")

    if not source.exists():
        pytest.skip("Test track not available")

    try:
        result = normalize_audio(source, output)

        assert result.exists()
        assert result == output
        assert output.stat().st_size > 0

        # Verify output is valid audio
        metadata = extract_metadata(output)
        assert metadata.duration_seconds > 0

    finally:
        # Clean up
        if output.exists():
            output.unlink()


def test_normalize_audio_nonexistent_source():
    """Test that nonexistent source raises ValueError."""
    with pytest.raises(ValueError, match="Source file not found"):
        normalize_audio(
            Path("/nonexistent/source.mp3"),
            Path("/tmp/output.mp3"),
        )
```

Run:
```bash
# Append to test file
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/tests/test_audio.py
[content above]
EOF
```

Expected: Tests added

**Step 3: Run normalization tests**

Run:
```bash
cd /srv/ai_radio
uv run pytest tests/test_audio.py::test_normalize_audio -v
```

Expected: Test passes, normalized file created and cleaned up

---

## Task 6: Database Asset Operations

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/db_assets.py`

**Step 1: Create database asset insertion module**

Create file `/srv/ai_radio/src/ai_radio/db_assets.py`:
```python
"""Database operations for asset management."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .audio import AudioMetadata


def insert_asset(
    db_path: Path,
    asset_id: str,
    asset_type: str,
    normalized_path: Path,
    metadata: AudioMetadata,
    original_path: Optional[Path] = None,
) -> None:
    """Insert asset record into database.

    Args:
        db_path: Path to SQLite database
        asset_id: SHA256 hash of file
        asset_type: Asset type ('music', 'break', 'bumper')
        normalized_path: Path to normalized audio file
        metadata: Extracted audio metadata
        original_path: Optional source file path

    Raises:
        sqlite3.IntegrityError: If asset_id already exists
        sqlite3.Error: On database errors
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Prepare metadata JSON
        metadata_json = json.dumps({
            "original_path": str(original_path) if original_path else None,
            "normalized": True,
            "loudness_target": -18.0,
            "true_peak": -1.0,
        })

        cursor.execute(
            """
            INSERT INTO assets (
                id, type, path, original_path,
                title, artist, album, duration_seconds,
                created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                asset_type,
                str(normalized_path),
                str(original_path) if original_path else None,
                metadata.title,
                metadata.artist,
                metadata.album,
                metadata.duration_seconds,
                datetime.now(timezone.utc).isoformat(),
                metadata_json,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def asset_exists(db_path: Path, asset_id: str) -> bool:
    """Check if asset already exists in database.

    Args:
        db_path: Path to SQLite database
        asset_id: SHA256 hash to check

    Returns:
        True if asset exists, False otherwise
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM assets WHERE id = ?", (asset_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_asset_count_by_type(db_path: Path, asset_type: str) -> int:
    """Get count of assets by type.

    Args:
        db_path: Path to SQLite database
        asset_type: Asset type to count

    Returns:
        Number of assets of given type
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM assets WHERE type = ?",
            (asset_type,),
        )
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/db_assets.py << 'EOF'
[content above]
EOF
```

Expected: File created

**Step 2: Create tests for database operations**

Create file `/srv/ai_radio/tests/test_db_assets.py`:
```python
"""Tests for database asset operations."""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from ai_radio.db_assets import (
    insert_asset,
    asset_exists,
    get_asset_count_by_type,
)
from ai_radio.audio import AudioMetadata


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            original_path TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            duration_seconds REAL NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


def test_insert_asset(temp_db):
    """Test inserting asset into database."""
    metadata = AudioMetadata(
        path=Path("/srv/ai_radio/assets/music/test.mp3"),
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        duration_seconds=180.5,
    )

    insert_asset(
        db_path=temp_db,
        asset_id="test_sha256_hash",
        asset_type="music",
        normalized_path=Path("/srv/ai_radio/assets/music/test.mp3"),
        metadata=metadata,
        original_path=Path("/srv/ai_radio/assets/source_music/test.mp3"),
    )

    # Verify insertion
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM assets WHERE id = ?", ("test_sha256_hash",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[1] == "music"  # type
    assert row[4] == "Test Track"  # title


def test_asset_exists(temp_db):
    """Test checking if asset exists."""
    assert not asset_exists(temp_db, "nonexistent_id")

    metadata = AudioMetadata(
        path=Path("/test.mp3"),
        duration_seconds=100.0,
    )

    insert_asset(
        db_path=temp_db,
        asset_id="existing_id",
        asset_type="music",
        normalized_path=Path("/test.mp3"),
        metadata=metadata,
    )

    assert asset_exists(temp_db, "existing_id")


def test_get_asset_count_by_type(temp_db):
    """Test counting assets by type."""
    assert get_asset_count_by_type(temp_db, "music") == 0

    # Insert two music assets
    for i in range(2):
        metadata = AudioMetadata(
            path=Path(f"/test{i}.mp3"),
            duration_seconds=100.0,
        )
        insert_asset(
            db_path=temp_db,
            asset_id=f"id_{i}",
            asset_type="music",
            normalized_path=Path(f"/test{i}.mp3"),
            metadata=metadata,
        )

    assert get_asset_count_by_type(temp_db, "music") == 2
    assert get_asset_count_by_type(temp_db, "break") == 0
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/tests/test_db_assets.py << 'EOF'
[content above]
EOF
```

Expected: Test file created

**Step 3: Run database tests**

Run:
```bash
cd /srv/ai_radio
uv run pytest tests/test_db_assets.py -v
```

Expected: All tests pass

---

## Task 7: Ingest Script Implementation

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/ingest.py`

**Step 1: Create ingest script with progress logging**

Create file `/srv/ai_radio/src/ai_radio/ingest.py`:
```python
"""Music library ingestion script."""

import sys
import logging
from pathlib import Path
from typing import List

from .audio import extract_metadata, normalize_audio
from .db_assets import insert_asset, asset_exists
from .config import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav"}


def discover_audio_files(source_dir: Path) -> List[Path]:
    """Recursively discover audio files in source directory.

    Args:
        source_dir: Root directory to search

    Returns:
        List of audio file paths
    """
    if not source_dir.exists():
        raise ValueError(f"Source directory not found: {source_dir}")

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(source_dir.rglob(f"*{ext}"))

    return sorted(files)


def ingest_file(
    source_path: Path,
    output_dir: Path,
    db_path: Path,
    force: bool = False,
) -> bool:
    """Ingest single audio file: normalize, extract metadata, store in DB.

    Args:
        source_path: Source audio file
        output_dir: Directory for normalized output
        db_path: SQLite database path
        force: If True, re-ingest even if already exists

    Returns:
        True if ingested, False if skipped (already exists)

    Raises:
        Exception: On processing errors
    """
    try:
        # Extract metadata from source
        logger.info(f"Processing: {source_path.name}")
        metadata = extract_metadata(source_path)

        # Generate asset ID from source file
        asset_id = metadata.sha256_id

        # Skip if already exists (unless force)
        if not force and asset_exists(db_path, asset_id):
            logger.info(f"  ↳ Skipping (already exists): {asset_id[:16]}...")
            return False

        # Normalize audio
        output_path = output_dir / f"{asset_id}.mp3"
        logger.info(f"  ↳ Normalizing to: {output_path.name}")

        normalize_audio(
            source_path=source_path,
            output_path=output_path,
            loudness_target=-18.0,
            true_peak=-1.0,
        )

        # Extract metadata from normalized file (for duration verification)
        normalized_metadata = extract_metadata(output_path)

        # Insert into database
        logger.info(f"  ↳ Inserting to database: {asset_id[:16]}...")
        insert_asset(
            db_path=db_path,
            asset_id=asset_id,
            asset_type="music",
            normalized_path=output_path,
            metadata=normalized_metadata,
            original_path=source_path,
        )

        logger.info(f"  ✓ Success: {metadata.title} - {metadata.artist}")
        return True

    except Exception as e:
        logger.error(f"  ✗ Failed to ingest {source_path.name}: {e}")
        raise


def ingest_library(
    source_dir: Path,
    output_dir: Path,
    db_path: Path,
    force: bool = False,
    limit: int = 0,
) -> None:
    """Ingest entire music library.

    Args:
        source_dir: Directory containing source music files
        output_dir: Directory for normalized output files
        db_path: SQLite database path
        force: If True, re-ingest existing files
        limit: Maximum files to process (0 = unlimited)
    """
    logger.info(f"Starting music library ingestion")
    logger.info(f"  Source: {source_dir}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Database: {db_path}")

    # Discover files
    files = discover_audio_files(source_dir)
    total = len(files)

    if limit > 0:
        files = files[:limit]
        logger.info(f"Found {total} files, processing first {limit}")
    else:
        logger.info(f"Found {total} files")

    if total == 0:
        logger.warning("No audio files found!")
        return

    # Process files
    ingested = 0
    skipped = 0
    failed = 0

    for i, file_path in enumerate(files, 1):
        try:
            logger.info(f"[{i}/{len(files)}] {file_path.name}")

            if ingest_file(file_path, output_dir, db_path, force=force):
                ingested += 1
            else:
                skipped += 1

        except Exception as e:
            logger.error(f"Failed: {e}")
            failed += 1
            # Continue processing remaining files

    # Summary
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info(f"  Ingested: {ingested}")
    logger.info(f"  Skipped:  {skipped}")
    logger.info(f"  Failed:   {failed}")
    logger.info(f"  Total:    {ingested + skipped + failed}")


def main():
    """CLI entry point for ingest script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest music library with normalization"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/srv/ai_radio/assets/source_music"),
        help="Source music directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/srv/ai_radio/assets/music"),
        help="Normalized output directory",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("/srv/ai_radio/data/radio.db"),
        help="SQLite database path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest existing files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of files to process (0 = unlimited)",
    )

    args = parser.parse_args()

    try:
        ingest_library(
            source_dir=args.source,
            output_dir=args.output,
            db_path=args.db,
            force=args.force,
            limit=args.limit,
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/src/ai_radio/ingest.py << 'EOF'
[content above]
EOF
```

Expected: File created

**Step 2: Make ingest script executable via uv**

Add entry point to `/srv/ai_radio/pyproject.toml`:

```toml
[project.scripts]
ai-radio-ingest = "ai_radio.ingest:main"
```

Run:
```bash
# Add scripts section to pyproject.toml if not exists
cat << 'EOF' | sudo -u ai-radio tee -a /srv/ai_radio/pyproject.toml

[project.scripts]
ai-radio-ingest = "ai_radio.ingest:main"
EOF
```

Expected: Entry point added

**Step 3: Test ingest script with test track**

Run:
```bash
cd /srv/ai_radio
uv run ai-radio-ingest --limit 1
```

Expected: Test track ingested successfully, summary shows "Ingested: 1"

**Step 4: Verify database contains asset**

Run:
```bash
sqlite3 /srv/ai_radio/data/radio.db "SELECT id, title, artist, duration_seconds FROM assets LIMIT 1;"
```

Expected: One row with test track metadata

**Step 5: Verify normalized file exists**

Run:
```bash
ls -lh /srv/ai_radio/assets/music/
```

Expected: One .mp3 file with SHA256 filename

---

## Task 8: Integration Testing

**Files:**
- Create: `/srv/ai_radio/tests/test_ingest_integration.py`

**Step 1: Create end-to-end ingestion test**

Create file `/srv/ai_radio/tests/test_ingest_integration.py`:
```python
"""Integration tests for full ingestion pipeline."""

import pytest
import tempfile
import shutil
from pathlib import Path

from ai_radio.ingest import ingest_library, discover_audio_files
from ai_radio.db_assets import get_asset_count_by_type


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    source = Path(tempfile.mkdtemp())
    output = Path(tempfile.mkdtemp())
    db_file = Path(tempfile.mktemp(suffix=".db"))

    # Create database schema
    import sqlite3
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            original_path TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            duration_seconds REAL NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield source, output, db_file

    # Cleanup
    shutil.rmtree(source, ignore_errors=True)
    shutil.rmtree(output, ignore_errors=True)
    if db_file.exists():
        db_file.unlink()


def test_full_ingestion_pipeline(temp_dirs):
    """Test complete ingestion: discover → normalize → database."""
    source_dir, output_dir, db_path = temp_dirs

    # Copy test track to source directory
    test_track = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    if not test_track.exists():
        pytest.skip("Test track not available")

    shutil.copy(test_track, source_dir / "test.mp3")

    # Run ingestion
    ingest_library(
        source_dir=source_dir,
        output_dir=output_dir,
        db_path=db_path,
        force=False,
        limit=0,
    )

    # Verify results
    assert get_asset_count_by_type(db_path, "music") == 1
    assert len(list(output_dir.glob("*.mp3"))) == 1


def test_discover_audio_files():
    """Test audio file discovery."""
    source = Path("/srv/ai_radio/assets/source_music")

    if not source.exists():
        pytest.skip("Source directory not available")

    files = discover_audio_files(source)
    assert len(files) > 0
    assert all(f.suffix in {".mp3", ".flac", ".m4a", ".ogg", ".wav"} for f in files)
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/tests/test_ingest_integration.py << 'EOF'
[content above]
EOF
```

Expected: Test file created

**Step 2: Run integration tests**

Run:
```bash
cd /srv/ai_radio
uv run pytest tests/test_ingest_integration.py -v
```

Expected: All integration tests pass

---

## Task 9: Documentation

**Files:**
- Create: `/srv/ai_radio/docs/PHASE2_COMPLETE.md`

**Step 1: Document Phase 2 completion**

Create file `/srv/ai_radio/docs/PHASE2_COMPLETE.md`:
```markdown
# Phase 2: Asset Management - Complete

**Date:** $(date +%Y-%m-%d)
**Status:** ✅ Complete

## Summary

Music library ingestion pipeline is fully operational. Can ingest, normalize, and catalog audio files with complete metadata tracking.

## Implemented Components

### Audio Processing
- ✅ Metadata extraction (mutagen)
- ✅ Loudness normalization (-18 LUFS, -1.0 dBTP)
- ✅ SHA256 asset ID generation
- ✅ Atomic file operations

### Database Integration
- ✅ Asset insertion with metadata
- ✅ Duplicate detection (skip existing)
- ✅ Type-based queries
- ✅ Index for performance

### Ingest Script
- ✅ Recursive file discovery
- ✅ Progress logging
- ✅ Error handling (continue on failure)
- ✅ Force re-ingest option
- ✅ Batch limit control

## Usage

### Ingest Music Library

```bash
cd /srv/ai_radio
uv run ai-radio-ingest --source /path/to/music --limit 0
```

### Verify Ingestion

```bash
# Count music assets
sqlite3 /srv/ai_radio/data/radio.db "SELECT COUNT(*) FROM assets WHERE type='music';"

# List recent assets
sqlite3 /srv/ai_radio/data/radio.db "SELECT title, artist, duration_seconds FROM assets ORDER BY created_at DESC LIMIT 10;"
```

## Test Results

All unit and integration tests passing:
- `tests/test_audio.py` - Metadata extraction and normalization
- `tests/test_db_assets.py` - Database operations
- `tests/test_ingest_integration.py` - End-to-end pipeline

## Next Steps

Phase 3 will implement advanced Liquidsoap configuration:
- Multi-level fallback chain
- Break insertion logic
- Operator overrides
- Queue management

## SOW Compliance

✅ Section 4: `ingest.py` architecture
✅ Section 6: Assets table schema
✅ Section 8: Loudness targets (-18 LUFS, -1.0 dBTP)
✅ Section 8: ffmpeg-normalize usage
✅ Section 3: Non-Negotiable #5 (Atomic handoffs)
```

Run:
```bash
sudo -u ai-radio tee /srv/ai_radio/docs/PHASE2_COMPLETE.md << 'EOF'
[content above]
EOF
```

Expected: Documentation created

---

## Definition of Done

- [x] ffmpeg-normalize and mutagen dependencies installed
- [x] Database schema verified with type index
- [x] Directory structure created (source_music/, music/, tmp/)
- [x] Metadata extraction module implemented and tested
- [x] Audio normalization function implemented and tested
- [x] Database asset operations implemented and tested
- [x] Ingest script with CLI interface complete
- [x] Integration tests passing
- [x] Documentation complete

## Verification Commands

```bash
# 1. Verify dependencies
uv pip list | grep -E "mutagen|ffmpeg-normalize"

# 2. Verify database schema
sqlite3 /srv/ai_radio/data/radio.db ".schema assets"

# 3. Run all tests
cd /srv/ai_radio && uv run pytest -v

# 4. Test ingestion with limit
uv run ai-radio-ingest --limit 1

# 5. Verify asset in database
sqlite3 /srv/ai_radio/data/radio.db "SELECT COUNT(*) FROM assets;"

# 6. Verify normalized file exists
ls -lh /srv/ai_radio/assets/music/
```

All commands should complete successfully without errors.

---

## Notes

- **Idempotent**: Running ingest multiple times skips existing assets (unless --force)
- **Resumable**: Failed files are logged but don't stop batch processing
- **Production Ready**: Atomic file operations prevent corruption
- **Performance**: SHA256 hashing uses 8KB chunks for large files
- **Extensible**: Easy to add support for additional audio formats via mutagen
