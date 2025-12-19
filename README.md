# AI Radio

A Python-based audio asset management system for automated radio broadcasting, designed to work with Liquidsoap.

## Overview

AI Radio is a producer/consumer system where Python services handle audio ingestion, normalization, and metadata management, while Liquidsoap consumes the prepared assets for broadcasting.

## Current Status

**Phase 2: Asset Management** - COMPLETE
- Audio metadata extraction (MP3, FLAC)
- Broadcast-standard loudness normalization (EBU R128)
- SQLite asset database with content-addressable storage
- Comprehensive test coverage (23 tests)

## Features

- **Metadata Extraction**: Extracts title, artist, album, and duration from audio files using mutagen
- **Loudness Normalization**: Normalizes audio to -18 LUFS integrated loudness with -1.0 dBTP true peak using ffmpeg-normalize
- **Content-Addressable Storage**: SHA256-based asset IDs for deduplication
- **Database Management**: SQLite backend for asset tracking and retrieval
- **Robust Testing**: 100% test coverage with pytest

## Requirements

- Python 3.11+
- ffmpeg
- ffmpeg-normalize

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd clanker-radio

# Install dependencies using uv
uv sync

# Install system dependencies (macOS)
brew install ffmpeg

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install ffmpeg
```

## Usage

### Basic Asset Ingestion

```python
from pathlib import Path
import sqlite3
from ai_radio.ingest import ingest_audio_asset

# Connect to database
conn = sqlite3.connect("assets.db")

# Ingest an audio file
asset_id = ingest_audio_asset(
    source_path=Path("/path/to/music.mp3"),
    music_dir=Path("/srv/ai_radio/assets/normalized_music"),
    conn=conn,
    kind="music"
)

print(f"Ingested asset: {asset_id}")
```

### Extracting Metadata

```python
from pathlib import Path
from ai_radio.audio import extract_metadata

metadata = extract_metadata(Path("/path/to/music.mp3"))
print(f"Title: {metadata.title}")
print(f"Artist: {metadata.artist}")
print(f"Duration: {metadata.duration_sec}s")
print(f"SHA256 ID: {metadata.sha256_id}")
```

### Normalizing Audio

```python
from pathlib import Path
from ai_radio.audio import normalize_audio

result = normalize_audio(
    input_path=Path("/path/to/input.mp3"),
    output_path=Path("/path/to/output.mp3"),
    target_lufs=-18.0,
    true_peak=-1.0
)

print(f"Loudness: {result['loudness_lufs']} LUFS")
print(f"True Peak: {result['true_peak_dbtp']} dBTP")
```

## Architecture

### Producer/Consumer Model

```
Python Services (Producer)      Liquidsoap (Consumer)
├── Audio Ingestion        →    ├── Playlist Generation
├── Metadata Extraction    →    ├── Mixing & Transitions
├── Normalization          →    ├── Live Broadcasting
└── Database Management    →    └── Stream Output
```

### Database Schema

Assets are stored with the following structure:

```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,              -- SHA256 hash
    path TEXT UNIQUE NOT NULL,        -- File path
    kind TEXT NOT NULL,               -- music/break/bed/safety
    duration_sec REAL NOT NULL,       -- Duration in seconds
    loudness_lufs REAL,               -- Integrated loudness
    true_peak_dbtp REAL,              -- True peak level
    energy_level INTEGER,             -- 0-100 scale
    title TEXT,                       -- Track title
    artist TEXT,                      -- Artist name
    album TEXT,                       -- Album name
    created_at TEXT NOT NULL          -- ISO 8601 timestamp
);
```

### Content-Addressable Storage

Files are identified by SHA256 hash of their contents, enabling:
- Automatic deduplication
- Reliable change detection
- Content verification

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ai_radio --cov-report=html

# Run specific test file
uv run pytest tests/test_audio.py -v
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Type checking
uv run mypy src/

# Format code
uv run ruff format .
```

## Broadcast Standards

This system follows EBU R128 loudness recommendations:

- **Target Loudness**: -18 LUFS (integrated)
- **True Peak**: -1.0 dBTP
- **Sample Rate**: 44.1 kHz
- **Encoding**: MP3 @ 192kbps

## License

[Add license information]

## Contributing

[Add contribution guidelines]
