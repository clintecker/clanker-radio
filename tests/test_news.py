"""Tests for RSS news feed client.

Test coverage:
- Successful headline fetching
- Multiple feed aggregation
- Headline deduplication
- Feed parsing error handling
- Empty feed handling
- Network error handling
"""

from datetime import datetime
from unittest.mock import Mock, patch
from time import struct_time

import httpx
import pytest

from ai_radio.news import RSSNewsClient, NewsData, NewsHeadline, get_news


class TestRSSNewsClient:
    """Tests for RSSNewsClient."""

    def test_initialization_uses_config(self):
        """RSSNewsClient should load feed URLs from config."""
        client = RSSNewsClient()

        assert len(client.feed_urls) == 2
        assert "npr.org" in client.feed_urls[0]
        assert "chicagotribune.com" in client.feed_urls[1]
        assert client.max_headlines_per_feed == 5
        assert client.timeout == 10

    def test_fetch_headlines_success(self):
        """fetch_headlines should return NewsData with headlines from valid feed."""
        client = RSSNewsClient()

        # Create mock entries as objects with attributes (not dicts)
        entry1 = Mock()
        entry1.title = "Breaking: Test Story"
        entry1.link = "https://example.com/story1"
        entry1.published_parsed = struct_time((2025, 12, 19, 12, 0, 0, 3, 353, 0))
        entry1.get = lambda k, d=None: getattr(entry1, k, d)

        entry2 = Mock()
        entry2.title = "Another Story"
        entry2.link = "https://example.com/story2"
        entry2.published_parsed = struct_time((2025, 12, 19, 11, 0, 0, 3, 353, 0))
        entry2.get = lambda k, d=None: getattr(entry2, k, d)

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test News"}
        mock_feed.entries = [entry1, entry2]

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) == 2
            assert news.headlines[0].title == "Breaking: Test Story"
            assert news.headlines[0].source == "Test News"
            assert news.headlines[0].link == "https://example.com/story1"
            assert news.headlines[0].published == datetime(2025, 12, 19, 12, 0, 0)
            assert news.source_count == 2  # Both configured feeds "succeeded"
            assert isinstance(news.timestamp, datetime)

    def test_fetch_headlines_multiple_feeds(self):
        """fetch_headlines should aggregate headlines from multiple feeds."""
        client = RSSNewsClient()

        def mock_get_side_effect(url, headers):
            if "npr" in url:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>NPR News</title>
                    <item><title>NPR Story 1</title><link>https://npr.org/1</link></item>
                    </channel></rss>"""
                return mock_response
            elif "tribune" in url:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>Test News Source</title>
                    <item><title>Test Story 1</title><link>https://testnews.com/1</link></item>
                    </channel></rss>"""
                return mock_response
            return Mock(bozo=True, entries=[])

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) == 2
            assert any("NPR" in h.title for h in news.headlines)
            assert any("Tribune" in h.title for h in news.headlines)
            assert news.source_count == 2

    def test_fetch_headlines_deduplication(self):
        """fetch_headlines should deduplicate identical headlines (case-insensitive)."""
        client = RSSNewsClient()

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Source"}
        mock_feed.entries = [
            {"title": "Breaking News", "link": "https://example.com/1", "published_parsed": None},
            {"title": "breaking news", "link": "https://example.com/2", "published_parsed": None},
            {"title": "Different Story", "link": "https://example.com/3", "published_parsed": None},
        ]

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            news = client.fetch_headlines()

            assert news is not None
            # Should have 2 unique headlines (one duplicate removed)
            assert len(news.headlines) == 2
            titles = [h.title for h in news.headlines]
            assert "Breaking News" in titles
            assert "Different Story" in titles

    def test_fetch_headlines_parsing_error(self):
        """fetch_headlines should skip feeds with parsing errors."""
        client = RSSNewsClient()

        def mock_get_side_effect(url, headers):
            if "npr" in url:
                # First feed returns malformed XML that causes parsing error
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"<invalid xml>"
                return mock_response
            elif "tribune" in url:
                # Second feed succeeds
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>Working Feed</title>
                    <item><title>Valid Story</title><link>https://example.com/1</link></item>
                    </channel></rss>"""
                return mock_response
            return Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) == 1
            assert news.headlines[0].title == "Valid Story"
            assert news.source_count == 1  # Only one feed succeeded

    def test_fetch_headlines_empty_feed(self):
        """fetch_headlines should skip feeds with no entries."""
        client = RSSNewsClient()

        def mock_get_side_effect(url, headers):
            if "npr" in url:
                # First feed is empty (no items)
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>Empty Feed</title></channel></rss>"""
                return mock_response
            elif "tribune" in url:
                # Second feed has content
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>Working Feed</title>
                    <item><title>Valid Story</title><link>https://example.com/1</link></item>
                    </channel></rss>"""
                return mock_response
            return Mock()

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) == 1
            assert news.source_count == 1

    def test_fetch_headlines_all_feeds_fail(self):
        """fetch_headlines should return None when all feeds fail."""
        client = RSSNewsClient()

        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_feed.entries = []

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            news = client.fetch_headlines()

            assert news is None

    def test_fetch_headlines_max_per_feed(self):
        """fetch_headlines should limit headlines per feed to max_headlines_per_feed."""
        client = RSSNewsClient()
        client.max_headlines_per_feed = 3

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Feed"}
        mock_feed.entries = [
            {"title": f"Story {i}", "link": f"https://example.com/{i}", "published_parsed": None}
            for i in range(10)  # 10 entries
        ]

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            news = client.fetch_headlines()

            assert news is not None
            # Should have 3 headlines per feed × 2 feeds = 6 total
            # (but config has 2 feeds, so with mocking both return same feed, we get 6)
            assert len(news.headlines) <= 6

    def test_fetch_headlines_missing_fields(self):
        """fetch_headlines should handle entries with missing fields gracefully."""
        client = RSSNewsClient()

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Feed"}
        mock_feed.entries = [
            {},  # Empty entry - will become "Untitled" with no link
            {"title": "Title Only"},  # Missing link
            {"title": "Another Title", "link": ""},  # Empty link string
        ]

        with patch("feedparser.parse") as mock_parse:
            mock_parse.return_value = mock_feed

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) == 3
            assert news.headlines[0].title == "Untitled"
            assert news.headlines[0].link == ""
            assert news.headlines[1].title == "Title Only"
            assert news.headlines[1].link == ""
            assert news.headlines[2].title == "Another Title"
            assert news.headlines[2].link == ""

    def test_fetch_headlines_network_timeout(self):
        """fetch_headlines should handle network timeouts gracefully."""
        client = RSSNewsClient()

        # Mock httpx to simulate timeout on first feed, success on second
        def mock_get_side_effect(url, headers):
            if "npr" in url:
                raise httpx.TimeoutException("Request timed out")
            # Second feed returns valid RSS XML
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.content = b"""<?xml version="1.0"?>
                <rss><channel><title>Tribune</title>
                <item><title>Tribune Story</title><link>https://example.com/1</link></item>
                </channel></rss>"""
            return mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            # Should still succeed with data from the second feed
            assert news is not None
            assert len(news.headlines) == 1
            assert news.headlines[0].title == "Tribune Story"
            assert news.source_count == 1  # Only one feed succeeded


class TestGetNewsConvenience:
    """Tests for get_news() convenience function."""

    def test_get_news_success(self):
        """get_news should return NewsData on success."""
        mock_news = NewsData(
            headlines=[
                NewsHeadline(title="Test Story", source="Test", link="https://example.com/1")
            ],
            timestamp=datetime.now(),
            source_count=1,
        )

        with patch("ai_radio.news.RSSNewsClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_headlines.return_value = mock_news
            mock_client_class.return_value = mock_client

            result = get_news()

            assert result == mock_news

    def test_get_news_failure(self):
        """get_news should return None on fetch failure."""
        with patch("ai_radio.news.RSSNewsClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_headlines.return_value = None
            mock_client_class.return_value = mock_client

            result = get_news()

            assert result is None
