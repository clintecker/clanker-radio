"""Tests for ContentSourcesConfig domain configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ai_radio.config.content_sources import ContentSourcesConfig


class TestContentSourcesConfig:
    """Test ContentSourcesConfig domain configuration."""

    # NWS Weather Configuration Tests
    def test_default_nws_office(self):
        """Test default NWS office code."""
        config = ContentSourcesConfig()
        assert config.nws_office is None

    def test_nws_office_from_env(self):
        """Test NWS office code from environment."""
        with patch.dict(os.environ, {"RADIO_NWS_OFFICE": "LOX"}):
            config = ContentSourcesConfig()
            assert config.nws_office == "LOX"

    def test_default_nws_grid_x(self):
        """Test default NWS grid X coordinate."""
        config = ContentSourcesConfig()
        assert config.nws_grid_x is None

    def test_nws_grid_x_from_env(self):
        """Test NWS grid X coordinate from environment."""
        with patch.dict(os.environ, {"RADIO_NWS_GRID_X": "42"}):
            config = ContentSourcesConfig()
            assert config.nws_grid_x == 42

    def test_default_nws_grid_y(self):
        """Test default NWS grid Y coordinate."""
        config = ContentSourcesConfig()
        assert config.nws_grid_y is None

    def test_nws_grid_y_from_env(self):
        """Test NWS grid Y coordinate from environment."""
        with patch.dict(os.environ, {"RADIO_NWS_GRID_Y": "73"}):
            config = ContentSourcesConfig()
            assert config.nws_grid_y == 73

    # News RSS Feeds Tests
    def test_default_news_rss_feeds(self):
        """Test default news RSS feeds."""
        config = ContentSourcesConfig()
        assert config.news_rss_feeds == {
            "news": [
                "https://feeds.npr.org/1001/rss.xml",
            ],
        }

    def test_news_rss_feeds_from_env(self):
        """Test news RSS feeds from environment."""
        feeds = {"tech": ["https://example.com/tech.xml"], "sports": ["https://example.com/sports.xml"]}
        import json
        with patch.dict(os.environ, {"RADIO_NEWS_RSS_FEEDS": json.dumps(feeds)}):
            config = ContentSourcesConfig()
            assert config.news_rss_feeds == feeds

    def test_news_rss_feeds_immutable_default(self):
        """Test that news_rss_feeds default is not shared between instances."""
        config1 = ContentSourcesConfig()
        config2 = ContentSourcesConfig()
        config1.news_rss_feeds["test"] = ["https://example.com/test.xml"]
        assert "test" not in config2.news_rss_feeds

    # Hallucinated News Tests
    def test_default_hallucinate_news(self):
        """Test default hallucinate_news setting."""
        config = ContentSourcesConfig()
        assert config.hallucinate_news is False

    def test_hallucinate_news_from_env(self):
        """Test hallucinate_news from environment."""
        with patch.dict(os.environ, {"RADIO_HALLUCINATE_NEWS": "true"}):
            config = ContentSourcesConfig()
            assert config.hallucinate_news is True

    def test_default_hallucination_chance(self):
        """Test default hallucination_chance."""
        config = ContentSourcesConfig()
        assert config.hallucination_chance == 0.0

    def test_hallucination_chance_from_env(self):
        """Test hallucination_chance from environment."""
        with patch.dict(os.environ, {"RADIO_HALLUCINATION_CHANCE": "0.25"}):
            config = ContentSourcesConfig()
            assert config.hallucination_chance == 0.25

    def test_hallucination_chance_validation_too_low(self):
        """Test hallucination_chance validation rejects values below 0.0."""
        with pytest.raises(ValidationError):
            ContentSourcesConfig(hallucination_chance=-0.1)

    def test_hallucination_chance_validation_too_high(self):
        """Test hallucination_chance validation rejects values above 1.0."""
        with pytest.raises(ValidationError):
            ContentSourcesConfig(hallucination_chance=1.5)

    def test_hallucination_chance_validation_lower_bound(self):
        """Test hallucination_chance accepts 0.0."""
        config = ContentSourcesConfig(hallucination_chance=0.0)
        assert config.hallucination_chance == 0.0

    def test_hallucination_chance_validation_upper_bound(self):
        """Test hallucination_chance accepts 1.0."""
        config = ContentSourcesConfig(hallucination_chance=1.0)
        assert config.hallucination_chance == 1.0

    def test_default_hallucination_kernels(self):
        """Test default hallucination_kernels."""
        config = ContentSourcesConfig()
        assert config.hallucination_kernels == []

    def test_hallucination_kernels_from_env(self):
        """Test hallucination_kernels from environment."""
        kernels = ["technology", "science", "politics"]
        import json
        with patch.dict(os.environ, {"RADIO_HALLUCINATION_KERNELS": json.dumps(kernels)}):
            config = ContentSourcesConfig()
            assert config.hallucination_kernels == kernels

    def test_hallucination_kernels_immutable_default(self):
        """Test that hallucination_kernels default is not shared between instances."""
        config1 = ContentSourcesConfig()
        config2 = ContentSourcesConfig()
        config1.hallucination_kernels.append("test")
        assert "test" not in config2.hallucination_kernels
