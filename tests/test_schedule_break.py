"""Tests for break scheduler module.

Test coverage:
- Stale break detection and rejection
- Fresh break selection
- Freshness threshold from config
"""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ai_radio.break_scheduler import get_fresh_break, StaleBreakError


class TestGetFreshBreak:
    """Tests for get_fresh_break function."""

    def test_stale_break_raises_error(self, tmp_path):
        """Stale breaks should raise StaleBreakError."""
        # Create a break file
        break_file = tmp_path / "break_20260108_120000.mp3"
        break_file.write_bytes(b"fake audio data")

        # Make the file appear old (60 minutes ago)
        old_mtime = time.time() - (60 * 60)
        import os
        os.utime(break_file, (old_mtime, old_mtime))

        # Mock config to use our temp directory and 50 min threshold
        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 50

        with patch("ai_radio.break_scheduler.config", mock_config):
            with pytest.raises(StaleBreakError) as exc_info:
                get_fresh_break(tmp_path)

            assert exc_info.value.age_minutes == 60
            assert exc_info.value.threshold_minutes == 50
            assert "break_20260108_120000.mp3" in str(exc_info.value)

    def test_fresh_break_returned(self, tmp_path):
        """Fresh breaks should be returned successfully."""
        # Create a break file
        break_file = tmp_path / "break_20260108_170000.mp3"
        break_file.write_bytes(b"fake audio data")

        # File was just created, so mtime is now (fresh)

        # Mock config
        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 50

        with patch("ai_radio.break_scheduler.config", mock_config):
            result = get_fresh_break(tmp_path)

        assert result == break_file

    def test_freshness_threshold_from_config(self, tmp_path):
        """Freshness threshold should come from config.operational.break_freshness_minutes."""
        # Create a break file
        break_file = tmp_path / "break_20260108_140000.mp3"
        break_file.write_bytes(b"fake audio data")

        # Make the file 40 minutes old
        old_mtime = time.time() - (40 * 60)
        import os
        os.utime(break_file, (old_mtime, old_mtime))

        # Mock config with 30 minute threshold (so 40 min old is stale)
        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 30

        with patch("ai_radio.break_scheduler.config", mock_config):
            with pytest.raises(StaleBreakError) as exc_info:
                get_fresh_break(tmp_path)

            assert exc_info.value.threshold_minutes == 30

    def test_break_just_under_threshold_is_fresh(self, tmp_path):
        """Break just under threshold should be considered fresh."""
        # Create a break file
        break_file = tmp_path / "break_20260108_160000.mp3"
        break_file.write_bytes(b"fake audio data")

        # Make the file 49 minutes old (just under 50 min threshold)
        threshold_mtime = time.time() - (49 * 60)
        import os
        os.utime(break_file, (threshold_mtime, threshold_mtime))

        # Mock config with 50 minute threshold
        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 50

        with patch("ai_radio.break_scheduler.config", mock_config):
            # Should NOT raise - exactly at threshold means not over
            result = get_fresh_break(tmp_path)

        assert result == break_file

    def test_no_breaks_raises_file_not_found(self, tmp_path):
        """Empty breaks directory should raise FileNotFoundError."""
        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 50

        with patch("ai_radio.break_scheduler.config", mock_config):
            with pytest.raises(FileNotFoundError) as exc_info:
                get_fresh_break(tmp_path)

            assert "No breaks available" in str(exc_info.value)

    def test_selects_newest_break(self, tmp_path):
        """Should select the newest break file by mtime."""
        # Create two break files
        old_break = tmp_path / "break_20260108_100000.mp3"
        old_break.write_bytes(b"old audio")

        new_break = tmp_path / "break_20260108_160000.mp3"
        new_break.write_bytes(b"new audio")

        # Make old_break actually old
        import os
        old_mtime = time.time() - (120 * 60)  # 2 hours ago
        os.utime(old_break, (old_mtime, old_mtime))

        # new_break keeps its current mtime (fresh)

        mock_config = MagicMock()
        mock_config.paths.breaks_path = tmp_path
        mock_config.operational.break_freshness_minutes = 50

        with patch("ai_radio.break_scheduler.config", mock_config):
            result = get_fresh_break(tmp_path)

        assert result == new_break


class TestStaleBreakError:
    """Tests for StaleBreakError exception."""

    def test_error_message_format(self, tmp_path):
        """Error message should contain all relevant info."""
        break_file = tmp_path / "break_test.mp3"
        error = StaleBreakError(break_file, age_minutes=75, threshold_minutes=50)

        message = str(error)
        assert "break_test.mp3" in message
        assert "75 minutes old" in message
        assert "threshold: 50 minutes" in message
        assert "Break generation may be failing" in message

    def test_error_attributes(self, tmp_path):
        """Error should expose attributes for programmatic access."""
        break_file = tmp_path / "break_test.mp3"
        error = StaleBreakError(break_file, age_minutes=75, threshold_minutes=50)

        assert error.break_file == break_file
        assert error.age_minutes == 75
        assert error.threshold_minutes == 50
