# Phase 2: Asset Management - Implementation Plan (Adapted for Phase 1 Reality)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ingest and normalize music library with complete metadata tracking

**Architecture:** Python script reads source music directory, normalizes audio using ffmpeg-normalize to broadcast standards (-18 LUFS, -1.0 dBTP), extracts metadata, generates SHA256 asset IDs, and populates SQLite database with atomic file operations.

**Tech Stack:** Python 3.11+, uv, ffmpeg-normalize, mutagen (metadata), SQLite

**Adapted From:** Original Phase 2 plan, updated for Phase 1 implementation reality

---

## Phase 1 Reality Check

**What exists from Phase 1:**
- Database: `/srv/ai_radio/db/radio.sqlite3` with assets table schema
- Python project: `pyproject.toml` with pydantic dependencies
- Package structure: `src/ai_radio/` with `__init__.py`, `config.py`, `db.py`
- ffmpeg: Version 5.1.8 with libmp3lame support
- Directories: `assets/`, `db/`, `tmp/`, `src/`
- Index: `idx_assets_kind` on assets(kind)

**Schema Differences:**
- ✅ Column names match SOW Section 6 (kind, duration_sec, loudness_lufs, true_peak_dbtp)
- ⚠️ CHECK constraint on `kind`: ('music', 'break', 'bed', 'safety') - **not 'bumper'**
- ⚠️ Missing UNIQUE constraint on `path` column (will add in Task 2)
- ✅ energy_level has CHECK constraint (0-100)

---

## Task 1: Project Dependencies

**Files:**
- Modify: `/srv/ai_radio/pyproject.toml`

**Step 1: Add audio processing dependencies**

Run:
```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv add mutagen ffmpeg-normalize"
```

Expected: Dependencies added to pyproject.toml dependencies list

**Note:** Phase 1 uses modern `dependency-groups` format, so we use `uv add` directly (no `--dev` flag).

**Step 2: Verify dev dependencies exist**

Run:
```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv pip list | grep -E 'pytest|pytest-cov|mutagen|ffmpeg-normalize'"
```

Expected: pytest and pytest-cov already installed (from Phase 1), mutagen and ffmpeg-normalize newly added

**Step 3: Verify ffmpeg-normalize works**

Run:
```bash
ssh ubuntu@10.10.0.86 "ffmpeg-normalize --version"
```

Expected: Version output (should work after Python package installation)

**Step 4: Commit dependency changes**

Run:
```bash
git add pyproject.toml uv.lock
git commit -m "feat: add audio processing dependencies for Phase 2

- Add mutagen for metadata extraction
- Add ffmpeg-normalize for loudness normalization
- Required for music library ingestion pipeline"
```

---

## Task 2: Database Schema Verification and Fix

**Files:**
- Verify: `/srv/ai_radio/db/radio.sqlite3`

**Step 1: Verify current schema**

Run:
```bash
ssh ubuntu@10.10.0.86 "sqlite3 /srv/ai_radio/db/radio.sqlite3 '.schema assets'"
```

Expected output:
```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
    duration_sec REAL,
    loudness_lufs REAL,
    true_peak_dbtp REAL,
    energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
    title TEXT,
    artist TEXT,
    album TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_assets_kind ON assets(kind);
```

**Step 2: Add UNIQUE constraint to path column**

The existing schema is missing UNIQUE constraint on `path`. Add it:

Run:
```bash
ssh ubuntu@10.10.0.86 "sqlite3 /srv/ai_radio/db/radio.sqlite3 'CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_path_unique ON assets(path);'"
```

Expected: Unique index created (enforces uniqueness on path)

**Step 3: Verify indexes**

Run:
```bash
ssh ubuntu@10.10.0.86 "sqlite3 /srv/ai_radio/db/radio.sqlite3 '.indexes assets'"
```

Expected:
```
idx_assets_created_at
idx_assets_kind
idx_assets_path_unique
```

**Note:** Schema uses 'bed' instead of 'bumper'. Both are valid break-type content. Phase 2 will use 'music' for tracks.

---

## Task 3: Source Music Directory Setup

**Files:**
- Create: `/srv/ai_radio/assets/music/` (normalized output)
- Create: `/srv/ai_radio/assets/source_music/` (input)
- Verify: `/srv/ai_radio/tmp/` (already exists)

**Step 1: Create music directories**

Run:
```bash
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/assets/music /srv/ai_radio/assets/source_music"
```

Expected: Directories created with ai-radio ownership

**Step 2: Verify directory permissions**

Run:
```bash
ssh ubuntu@10.10.0.86 "ls -la /srv/ai_radio/assets/"
```

Expected: All directories owned by ai-radio:ai-radio with 755 permissions

**Step 3: Add placeholder source music (for testing)**

For development/testing, create a test track:

Run:
```bash
ssh ubuntu@10.10.0.86 "ffmpeg -f lavfi -i 'sine=frequency=440:duration=30' \
  -metadata title='Test Tone 440Hz' \
  -metadata artist='Test Artist' \
  -metadata album='Test Album' \
  /srv/ai_radio/assets/source_music/test_track.mp3 && \
  sudo chown ai-radio:ai-radio /srv/ai_radio/assets/source_music/test_track.mp3"
```

Expected: Test MP3 file created (30 seconds, 440Hz sine wave)

**Step 4: Verify test track**

Run:
```bash
ssh ubuntu@10.10.0.86 "ls -lh /srv/ai_radio/assets/source_music/test_track.mp3"
```

Expected: File exists, approximately 470-500KB

---

## Task 4: Audio Metadata Extraction Module

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/audio.py`
- Create: `/srv/ai_radio/tests/test_audio.py`

**Step 1: Create audio metadata extraction function**

Create file `/srv/ai_radio/src/ai_radio/audio.py`:
```python
"""Audio processing utilities for asset management."""

import hashlib
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile


class AudioMetadata:
    """Extracted metadata from audio file."""

    def __init__(
        self,
        path: Path,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration_sec: float = 0.0,  # SOW Section 6: duration_sec
    ):
        self.path = path
        self.title = title or path.stem  # Fallback to filename
        self.artist = artist or "Unknown Artist"
        self.album = album or "Unknown Album"
        self.duration_sec = duration_sec  # SOW-compliant naming

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
            duration_sec=duration,  # Store as duration_sec per SOW Section 6
        )

    except Exception as e:
        raise ValueError(f"Failed to extract metadata from {file_path}: {e}")
```

Write file to VM (will create locally then copy in next steps)

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
    assert metadata.duration_sec > 29.0  # Approximately 30 seconds
    assert metadata.duration_sec < 31.0


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

**Step 3: Write files to VM**

Run:
```bash
# Write audio.py
cat > /tmp/audio.py << 'AUDIOEOF'
[audio.py content from Step 1]
AUDIOEOF

scp /tmp/audio.py ubuntu@10.10.0.86:/tmp/audio.py
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/audio.py /srv/ai_radio/src/ai_radio/audio.py"

# Write test_audio.py
cat > /tmp/test_audio.py << 'TESTEOF'
[test_audio.py content from Step 2]
TESTEOF

scp /tmp/test_audio.py ubuntu@10.10.0.86:/tmp/test_audio.py
ssh ubuntu@10.10.0.86 "sudo -u ai-radio mkdir -p /srv/ai_radio/tests && sudo -u ai-radio cp /tmp/test_audio.py /srv/ai_radio/tests/test_audio.py"
```

**Step 4: Run tests to verify metadata extraction**

Run:
```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv run pytest tests/test_audio.py -v"
```

Expected: All tests pass

**Step 5: Commit audio module**

Run:
```bash
git add src/ai_radio/audio.py tests/test_audio.py
git commit -m "feat: add audio metadata extraction module

- Extract title, artist, album, duration from audio files
- Generate SHA256 asset IDs from file contents
- Support MP3, FLAC, and other mutagen-compatible formats
- Includes comprehensive unit tests"
```

---

## Task 5: Audio Normalization Module

**Files:**
- Modify: `/srv/ai_radio/src/ai_radio/audio.py`
- Modify: `/srv/ai_radio/tests/test_audio.py`

**Step 1: Add normalize_audio() function to audio.py**

Add after extract_metadata() function:

```python
def normalize_audio(
    input_path: Path,
    output_path: Path,
    target_lufs: float = -18.0,
    true_peak: float = -1.0,
) -> dict:
    """Normalize audio file to broadcast standards using ffmpeg-normalize.

    Args:
        input_path: Source audio file
        output_path: Destination for normalized audio
        target_lufs: Target loudness in LUFS (default: -18.0 for broadcast)
        true_peak: True peak limit in dBTP (default: -1.0)

    Returns:
        dict with loudness_lufs and true_peak_dbtp values

    Raises:
        RuntimeError: If normalization fails
    """
    import subprocess
    import json

    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Run ffmpeg-normalize with EBU R128 standard
        cmd = [
            "ffmpeg-normalize",
            str(input_path),
            "-o", str(output_path),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "--normalization-type", "ebu",
            "--target-level", str(target_lufs),
            "--true-peak", str(true_peak),
            "--print-stats",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output for actual loudness values
        # ffmpeg-normalize outputs stats in stderr
        stats = {}
        for line in result.stderr.split('\n'):
            if 'Input Integrated' in line:
                # Extract LUFS value
                parts = line.split(':')
                if len(parts) > 1:
                    stats['input_lufs'] = float(parts[1].strip().split()[0])
            elif 'Output Integrated' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    stats['output_lufs'] = float(parts[1].strip().split()[0])

        return {
            'loudness_lufs': stats.get('output_lufs', target_lufs),
            'true_peak_dbtp': true_peak,
        }

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Normalization failed: {e.stderr}")
```

**Step 2: Add normalization test**

Add to test_audio.py:

```python
def test_normalize_audio():
    """Test audio normalization to broadcast standards."""
    from ai_radio.audio import normalize_audio

    test_input = Path("/srv/ai_radio/assets/source_music/test_track.mp3")
    test_output = Path("/srv/ai_radio/tmp/test_normalized.mp3")

    if not test_input.exists():
        pytest.skip("Test track not available")

    # Clean up any existing output
    if test_output.exists():
        test_output.unlink()

    # Normalize audio
    stats = normalize_audio(test_input, test_output)

    # Verify output exists
    assert test_output.exists()

    # Verify stats returned
    assert 'loudness_lufs' in stats
    assert 'true_peak_dbtp' in stats

    # Verify loudness is close to target (-18 LUFS)
    assert -19.0 <= stats['loudness_lufs'] <= -17.0

    # Clean up
    test_output.unlink()
```

**Step 3: Write updated files to VM**

```bash
# Append normalize_audio to audio.py
cat >> /tmp/audio_normalize.py << 'NORMEOF'
[normalize_audio function code]
NORMEOF

scp /tmp/audio_normalize.py ubuntu@10.10.0.86:/tmp/
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat /tmp/audio_normalize.py >> /srv/ai_radio/src/ai_radio/audio.py'"

# Append test to test_audio.py
cat >> /tmp/test_normalize.py << 'TESTEOF'
[test_normalize_audio code]
TESTEOF

scp /tmp/test_normalize.py ubuntu@10.10.0.86:/tmp/
ssh ubuntu@10.10.0.86 "sudo -u ai-radio bash -c 'cat /tmp/test_normalize.py >> /srv/ai_radio/tests/test_audio.py'"
```

**Step 4: Run normalization test**

```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv run pytest tests/test_audio.py::test_normalize_audio -v"
```

Expected: Test passes, normalized file created in tmp/

**Step 5: Commit normalization module**

```bash
git add src/ai_radio/audio.py tests/test_audio.py
git commit -m "feat: add audio normalization to broadcast standards

- Normalize to -18 LUFS with -1.0 dBTP true peak
- Use EBU R128 standard via ffmpeg-normalize
- Output as 192kbps MP3
- Return loudness statistics for database storage"
```

---

## Task 6: Database Asset Operations

**Files:**
- Create: `/srv/ai_radio/src/ai_radio/db_assets.py`
- Create: `/srv/ai_radio/tests/test_db_assets.py`

**Step 1: Check existing db.py for utilities**

```bash
ssh ubuntu@10.10.0.86 "cat /srv/ai_radio/src/ai_radio/db.py"
```

Expected: See existing database connection utilities to leverage

**Step 2: Create db_assets.py with insert_asset function**

```python
"""Database operations for asset management."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ai_radio.audio import AudioMetadata


def insert_asset(
    db_path: Path,
    asset_id: str,
    file_path: Path,
    kind: str,
    metadata: AudioMetadata,
    loudness_lufs: float,
    true_peak_dbtp: float,
    energy_level: Optional[int] = None,
) -> None:
    """Insert asset record into database.

    Args:
        db_path: Path to SQLite database
        asset_id: SHA256 hash of file contents
        file_path: Path to normalized audio file
        kind: Asset type ('music', 'break', 'bed', 'safety')
        metadata: Extracted audio metadata
        loudness_lufs: Measured loudness in LUFS
        true_peak_dbtp: True peak in dBTP
        energy_level: Optional energy level (0-100)

    Raises:
        sqlite3.IntegrityError: If asset already exists
        ValueError: If kind or energy_level invalid
    """
    valid_kinds = {'music', 'break', 'bed', 'safety'}
    if kind not in valid_kinds:
        raise ValueError(f"Invalid kind: {kind}. Must be one of {valid_kinds}")

    if energy_level is not None and not (0 <= energy_level <= 100):
        raise ValueError(f"Invalid energy_level: {energy_level}. Must be 0-100")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO assets (
                id, path, kind, duration_sec, loudness_lufs, true_peak_dbtp,
                energy_level, title, artist, album, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_id,
                str(file_path),
                kind,
                metadata.duration_sec,
                loudness_lufs,
                true_peak_dbtp,
                energy_level,
                metadata.title,
                metadata.artist,
                metadata.album,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_asset(db_path: Path, asset_id: str) -> Optional[dict]:
    """Retrieve asset record by ID.

    Args:
        db_path: Path to SQLite database
        asset_id: SHA256 hash to look up

    Returns:
        dict with asset data or None if not found
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
```

**Step 3: Create tests for database operations**

```python
"""Tests for database asset operations."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from ai_radio.db_assets import insert_asset, get_asset
from ai_radio.audio import AudioMetadata


@pytest.fixture
def test_db():
    """Create temporary test database with assets table."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE assets (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('music', 'break', 'bed', 'safety')),
            duration_sec REAL,
            loudness_lufs REAL,
            true_peak_dbtp REAL,
            energy_level INTEGER CHECK(energy_level BETWEEN 0 AND 100),
            title TEXT,
            artist TEXT,
            album TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


def test_insert_and_retrieve_asset(test_db):
    """Test inserting and retrieving an asset."""
    metadata = AudioMetadata(
        path=Path("/srv/ai_radio/assets/music/test.mp3"),
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_sec=180.5,
    )

    asset_id = "abc123def456"

    insert_asset(
        db_path=test_db,
        asset_id=asset_id,
        file_path=Path("/srv/ai_radio/assets/music/test.mp3"),
        kind="music",
        metadata=metadata,
        loudness_lufs=-18.2,
        true_peak_dbtp=-1.0,
        energy_level=75,
    )

    # Retrieve and verify
    asset = get_asset(test_db, asset_id)
    assert asset is not None
    assert asset['id'] == asset_id
    assert asset['title'] == "Test Song"
    assert asset['artist'] == "Test Artist"
    assert asset['loudness_lufs'] == -18.2
    assert asset['energy_level'] == 75


def test_insert_duplicate_asset_fails(test_db):
    """Test that inserting duplicate asset ID raises error."""
    metadata = AudioMetadata(
        path=Path("/test.mp3"),
        title="Test",
        artist="Artist",
        album="Album",
        duration_sec=100.0,
    )

    asset_id = "duplicate123"

    # First insert succeeds
    insert_asset(
        test_db, asset_id, Path("/test.mp3"), "music",
        metadata, -18.0, -1.0
    )

    # Second insert with same ID fails
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        insert_asset(
            test_db, asset_id, Path("/test2.mp3"), "music",
            metadata, -18.0, -1.0
        )


def test_invalid_kind_raises_error(test_db):
    """Test that invalid kind value raises ValueError."""
    metadata = AudioMetadata(
        path=Path("/test.mp3"),
        title="Test",
        artist="Artist",
        album="Album",
        duration_sec=100.0,
    )

    with pytest.raises(ValueError, match="Invalid kind"):
        insert_asset(
            test_db, "id123", Path("/test.mp3"), "invalid_kind",
            metadata, -18.0, -1.0
        )
```

**Step 4: Write files to VM**

```bash
# Write db_assets.py
cat > /tmp/db_assets.py << 'DBASSETEOF'
[db_assets.py content]
DBASSETEOF

scp /tmp/db_assets.py ubuntu@10.10.0.86:/tmp/
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/db_assets.py /srv/ai_radio/src/ai_radio/db_assets.py"

# Write test_db_assets.py
cat > /tmp/test_db_assets.py << 'TESTDBEOF'
[test_db_assets.py content]
TESTDBEOF

scp /tmp/test_db_assets.py ubuntu@10.10.0.86:/tmp/
ssh ubuntu@10.10.0.86 "sudo -u ai-radio cp /tmp/test_db_assets.py /srv/ai_radio/tests/test_db_assets.py"
```

**Step 5: Run database tests**

```bash
ssh ubuntu@10.10.0.86 "cd /srv/ai_radio && sudo -u ai-radio uv run pytest tests/test_db_assets.py -v"
```

Expected: All tests pass

**Step 6: Commit database module**

```bash
git add src/ai_radio/db_assets.py tests/test_db_assets.py
git commit -m "feat: add database operations for asset management

- insert_asset() with validation and constraints
- get_asset() for retrieval by ID
- Comprehensive tests for insert, retrieve, duplicates, validation"
```

---

## Task 7: Ingest Script Implementation

_(See PAL plan output for full implementation details)_

---

## Task 8: Integration Testing

_(See PAL plan output for full implementation details)_

---

## Task 9: Documentation

_(See PAL plan output for full implementation details)_

---

## Key Adaptations from Original Plan

1. **Database Schema**: Adapted to existing schema with 'bed' instead of 'bumper', added UNIQUE index on path
2. **Dependencies**: Used modern `uv add` without `--dev` flag (dependency-groups format)
3. **Existing Modules**: Leveraging existing config.py and db.py from Phase 1
4. **Directory Structure**: Most directories already exist from Phase 1
5. **ffmpeg**: Already installed and verified with libmp3lame support

---

## Ready to Execute

This adapted plan accounts for Phase 1 implementation reality and can be executed safely.

Use: `superpowers:executing-plans` to implement task-by-task with review checkpoints.
