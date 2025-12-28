"""Tests for SHA256 asset ID migration script."""

import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from migrate_to_sha256_ids import (
    create_orphan_asset,
    find_non_sha256_ids,
    is_orphan_id,
    is_sha256_hash,
    migrate_play_history,
    scan_and_hash_files,
    validate_migration,
)


class TestSHA256HashValidation:
    """Tests for SHA256 hash validation."""

    def test_is_sha256_hash_valid(self):
        """Valid SHA256 hashes are accepted."""
        valid_hash = "a" * 64  # 64 hex chars
        assert is_sha256_hash(valid_hash) is True

        # Real SHA256 from file
        real_hash = "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2"
        assert is_sha256_hash(real_hash) is True

        # Mixed case should work
        mixed_case = "AbCdEf0123456789" * 4
        assert is_sha256_hash(mixed_case.lower()) is True

    def test_is_sha256_hash_invalid(self):
        """Invalid hashes are rejected."""
        # Too short
        assert is_sha256_hash("abc123") is False

        # Too long
        assert is_sha256_hash("a" * 65) is False

        # Non-hex characters
        assert is_sha256_hash("g" * 64) is False
        assert is_sha256_hash("x" + "a" * 63) is False

        # Empty string
        assert is_sha256_hash("") is False

        # Filename stems
        assert is_sha256_hash("bumper_001") is False
        assert is_sha256_hash("break_weather_20250101") is False

        # UUID format (wrong format)
        assert is_sha256_hash("550e8400-e29b-41d4-a716-446655440000") is False


class TestOrphanIDValidation:
    """Tests for orphan ID detection."""

    def test_is_orphan_id(self):
        """Orphan prefix is correctly detected."""
        assert is_orphan_id("orphan_bumper_001") is True
        assert is_orphan_id("orphan_break_weather") is True
        assert is_orphan_id("orphan_") is True

    def test_is_orphan_id_negative(self):
        """Non-orphan IDs are rejected."""
        assert is_orphan_id("bumper_001") is False
        assert is_orphan_id("break_weather") is False
        assert is_orphan_id("a" * 64) is False
        assert is_orphan_id("") is False
        assert is_orphan_id("not_orphan_but_has_underscore") is False


class TestScanAndHashFiles:
    """Tests for directory scanning and file hashing."""

    def test_scan_and_hash_files(self, tmp_path, mocker):
        """Directory scanning finds and hashes audio files."""
        from ai_radio.audio import AudioMetadata

        audio_dir = tmp_path / "bumpers"
        audio_dir.mkdir()

        # Create test file
        mp3_file = audio_dir / "test_bumper.mp3"
        mp3_file.write_text("fake mp3 content")

        # Mock extract_metadata to return valid AudioMetadata
        mock_metadata = AudioMetadata(
            path=mp3_file,
            title="Test Bumper",
            artist="Test Artist",
            album="Test Album",
            duration_sec=10.0,
        )
        mock_extract = mocker.patch("migrate_to_sha256_ids.extract_metadata")
        mock_extract.return_value = mock_metadata

        # Mock sha256_id property
        mocker.patch.object(
            AudioMetadata,
            "sha256_id",
            new_callable=mocker.PropertyMock,
            return_value="a" * 64,
        )

        # Scan directory
        mapping = scan_and_hash_files(audio_dir, "bumper")

        # Verify mapping
        assert "test_bumper" in mapping
        sha256, path = mapping["test_bumper"]
        assert sha256 == "a" * 64
        assert path == mp3_file

    def test_scan_and_hash_files_empty_directory(self, tmp_path):
        """Empty directory returns empty mapping."""
        audio_dir = tmp_path / "empty"
        audio_dir.mkdir()

        mapping = scan_and_hash_files(audio_dir, "bumper")
        assert mapping == {}

    def test_scan_and_hash_files_nonexistent_directory(self, tmp_path):
        """Nonexistent directory returns empty mapping."""
        audio_dir = tmp_path / "nonexistent"

        mapping = scan_and_hash_files(audio_dir, "bumper")
        assert mapping == {}

    def test_scan_and_hash_files_handles_errors(self, tmp_path, mocker):
        """Files that fail to process are skipped."""
        audio_dir = tmp_path / "error_test"
        audio_dir.mkdir()

        # Create test file
        mp3_file = audio_dir / "broken.mp3"
        mp3_file.write_text("invalid")

        # Mock extract_metadata to raise exception
        mock_extract = mocker.patch("migrate_to_sha256_ids.extract_metadata")
        mock_extract.side_effect = ValueError("Invalid audio file")

        # Scan directory - should not crash
        mapping = scan_and_hash_files(audio_dir, "bumper")

        # Verify empty mapping (file was skipped)
        assert mapping == {}


class TestFindNonSHA256IDs:
    """Tests for finding non-SHA256 IDs in play_history."""

    def test_find_non_sha256_ids(self):
        """Identifies old filename-based IDs."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            # Create tables
            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert test data
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("bumper_001", "bumper", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("a" * 64, "break", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("old_break_weather", "break", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Find non-SHA256 IDs
            non_sha256 = find_non_sha256_ids(conn)

            # Verify results
            assert len(non_sha256) == 2
            assert ("bumper_001", "bumper") in non_sha256
            assert ("old_break_weather", "break") in non_sha256

            # SHA256 ID should not be in results
            sha256_ids = [id for id, _ in non_sha256]
            assert "a" * 64 not in sha256_ids

            conn.close()
            Path(tmp.name).unlink()


class TestCreateOrphanAsset:
    """Tests for creating orphan asset records."""

    def test_create_orphan_asset(self):
        """Creates synthetic asset record for deleted file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            # Create assets table
            conn.execute("""
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    kind TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
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

            # Create orphan asset
            orphan_id = create_orphan_asset(conn, "deleted_bumper", "bumper")

            # Verify orphan ID format
            assert orphan_id == "orphan_deleted_bumper"
            assert is_orphan_id(orphan_id)

            # Verify record in database
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets WHERE id = ?", (orphan_id,))
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == orphan_id  # id
            assert "[deleted]" in row[1]  # path
            assert row[2] == "bumper"  # kind
            assert row[3] == 0.0  # duration_sec

            conn.close()
            Path(tmp.name).unlink()

    def test_create_orphan_asset_idempotent(self):
        """Creating orphan twice returns same ID."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            conn.execute("""
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    kind TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
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

            # Create orphan twice
            orphan_id_1 = create_orphan_asset(conn, "deleted_file", "bumper")
            orphan_id_2 = create_orphan_asset(conn, "deleted_file", "bumper")

            assert orphan_id_1 == orphan_id_2

            # Verify only one record exists
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assets WHERE id = ?", (orphan_id_1,))
            count = cursor.fetchone()[0]
            assert count == 1

            conn.close()
            Path(tmp.name).unlink()


class TestMigratePlayHistory:
    """Tests for play_history migration."""

    def test_migrate_play_history_dry_run(self):
        """Dry-run mode doesn't modify database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            # Create table
            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert test data
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("old_bumper", "bumper", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Run migration in dry-run mode
            mapping = {"old_bumper": "a" * 64}
            stats = migrate_play_history(conn, mapping, {}, dry_run=True)

            # Verify statistics
            assert stats["updated"] == 1
            assert stats["unmapped"] == 0

            # Verify database not modified
            cursor = conn.cursor()
            cursor.execute("SELECT asset_id FROM play_history")
            asset_id = cursor.fetchone()[0]
            assert asset_id == "old_bumper"  # Still old ID

            conn.close()
            Path(tmp.name).unlink()

    def test_migrate_play_history_commits(self):
        """Actual migration updates database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            # Create table
            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert test data
            old_ids = ["bumper_001", "break_001", "bumper_002"]
            new_sha256s = ["a" * 64, "b" * 64, "c" * 64]

            for old_id in old_ids:
                conn.execute(
                    "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                    (old_id, "bumper", "2025-01-01T00:00:00Z"),
                )
            conn.commit()

            # Run migration
            mapping = {
                "bumper_001": new_sha256s[0],
                "break_001": new_sha256s[1],
                "bumper_002": new_sha256s[2],
            }
            stats = migrate_play_history(conn, mapping, {}, dry_run=False)

            # Verify statistics
            assert stats["updated"] == 3

            # Verify database updated
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT asset_id FROM play_history ORDER BY asset_id")
            updated_ids = [row[0] for row in cursor.fetchall()]

            assert set(updated_ids) == set(new_sha256s)
            assert all(is_sha256_hash(id) for id in updated_ids)

            conn.close()
            Path(tmp.name).unlink()

    def test_migrate_play_history_with_orphans(self):
        """Migration handles orphan mappings correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert test data
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("existing_file", "bumper", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("deleted_file", "break", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Run migration with both regular and orphan mappings
            mapping = {"existing_file": "a" * 64}
            orphan_mapping = {"deleted_file": "orphan_deleted_file"}
            stats = migrate_play_history(conn, mapping, orphan_mapping, dry_run=False)

            # Verify statistics
            assert stats["updated"] == 2

            # Verify database updated
            cursor = conn.cursor()
            cursor.execute("SELECT asset_id FROM play_history ORDER BY asset_id")
            updated_ids = [row[0] for row in cursor.fetchall()]

            assert "a" * 64 in updated_ids
            assert "orphan_deleted_file" in updated_ids

            conn.close()
            Path(tmp.name).unlink()


class TestValidateMigration:
    """Tests for migration validation."""

    def test_validate_migration_success(self):
        """Validation passes for clean state."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert valid SHA256 and orphan IDs
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("a" * 64, "bumper", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("orphan_old_file", "break", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Validate
            result = validate_migration(conn)
            assert result is True

            conn.close()
            Path(tmp.name).unlink()

    def test_validate_migration_failure(self):
        """Validation fails for mixed state."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)

            # Insert mix of valid and invalid IDs
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("a" * 64, "bumper", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO play_history (asset_id, kind, played_at) VALUES (?, ?, ?)",
                ("old_filename_stem", "break", "2025-01-01T00:00:00Z"),
            )
            conn.commit()

            # Validate
            result = validate_migration(conn)
            assert result is False

            conn.close()
            Path(tmp.name).unlink()

    def test_validate_migration_empty_database(self):
        """Validation passes for empty database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            conn = sqlite3.connect(tmp.name)

            conn.execute("""
                CREATE TABLE play_history (
                    id INTEGER PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    played_at TEXT NOT NULL
                )
            """)
            conn.commit()

            # Validate empty table
            result = validate_migration(conn)
            assert result is True

            conn.close()
            Path(tmp.name).unlink()
