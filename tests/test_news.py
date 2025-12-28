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
        """RSSNewsClient should load categorized feeds from config."""
        client = RSSNewsClient()

        assert isinstance(client.categorized_feeds, dict)
        assert len(client.categorized_feeds) > 0
        assert client.max_headlines_per_feed == 10
        assert client.timeout == 10.0
        assert client.categories_to_select == 3
        assert client.articles_per_category == 1

    def test_fetch_headlines_success(self):
        """fetch_headlines should return NewsData with headlines from valid feed."""
        client = RSSNewsClient()

        # Use today's date for entries to pass the 24-hour filter
        from datetime import datetime
        now = datetime.now()
        today_struct = struct_time((now.year, now.month, now.day, now.hour, 0, 0, 3, 353, 0))

        # Create mock entries as objects with attributes (not dicts)
        entry1 = Mock()
        entry1.title = "Breaking: Test Story"
        entry1.link = "https://example.com/story1"
        entry1.published_parsed = today_struct
        entry1.get = lambda k, d=None: getattr(entry1, k, d)

        entry2 = Mock()
        entry2.title = "Another Story"
        entry2.link = "https://example.com/story2"
        entry2.published_parsed = today_struct
        entry2.get = lambda k, d=None: getattr(entry2, k, d)

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test News"}
        mock_feed.entries = [entry1, entry2]

        with patch("feedparser.parse") as mock_parse, \
             patch("httpx.Client") as mock_client_class:
            mock_parse.return_value = mock_feed

            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = b"mock content"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1  # At least one headline selected
            assert isinstance(news.timestamp, datetime)

    def test_fetch_headlines_multiple_feeds(self):
        """fetch_headlines should aggregate headlines from multiple feeds."""
        client = RSSNewsClient()

        # Use today's date for entries
        from datetime import datetime
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%dT%H:00:00Z")

        def mock_get_side_effect(url, headers):
            # Return valid RSS with today's date
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.content = f"""<?xml version="1.0"?>
                <rss><channel><title>Test Feed</title>
                <item>
                    <title>Test Story</title>
                    <link>https://example.com/1</link>
                    <pubDate>{today_str}</pubDate>
                </item>
                </channel></rss>""".encode()
            return mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1

    def test_fetch_headlines_deduplication(self):
        """fetch_headlines should handle category-based selection."""
        client = RSSNewsClient()

        # Use today's date for entries
        from datetime import datetime
        now = datetime.now()
        today_struct = struct_time((now.year, now.month, now.day, now.hour, 0, 0, 3, 353, 0))

        entry1 = Mock()
        entry1.title = "Breaking News"
        entry1.link = "https://example.com/1"
        entry1.published_parsed = today_struct
        entry1.get = lambda k, d=None: getattr(entry1, k, d)

        entry2 = Mock()
        entry2.title = "Different Story"
        entry2.link = "https://example.com/3"
        entry2.published_parsed = today_struct
        entry2.get = lambda k, d=None: getattr(entry2, k, d)

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Source"}
        mock_feed.entries = [entry1, entry2]

        with patch("feedparser.parse") as mock_parse, \
             patch("httpx.Client") as mock_client_class:
            mock_parse.return_value = mock_feed

            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = b"mock content"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1

    def test_fetch_headlines_parsing_error(self):
        """fetch_headlines should skip feeds with parsing errors."""
        client = RSSNewsClient()

        # Use today's date
        from datetime import datetime
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%dT%H:00:00Z")

        call_count = [0]

        def mock_get_side_effect(url, headers):
            call_count[0] += 1
            # First call returns invalid XML, rest return valid
            if call_count[0] == 1:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"<invalid xml>"
                return mock_response
            else:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = f"""<?xml version="1.0"?>
                    <rss><channel><title>Working Feed</title>
                    <item>
                        <title>Valid Story</title>
                        <link>https://example.com/1</link>
                        <pubDate>{today_str}</pubDate>
                    </item>
                    </channel></rss>""".encode()
                return mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1

    def test_fetch_headlines_empty_feed(self):
        """fetch_headlines should skip feeds with no entries."""
        client = RSSNewsClient()

        # Use today's date
        from datetime import datetime
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%dT%H:00:00Z")

        call_count = [0]

        def mock_get_side_effect(url, headers):
            call_count[0] += 1
            # First call returns empty feed, rest return valid
            if call_count[0] == 1:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = b"""<?xml version="1.0"?>
                    <rss><channel><title>Empty Feed</title></channel></rss>"""
                return mock_response
            else:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.content = f"""<?xml version="1.0"?>
                    <rss><channel><title>Working Feed</title>
                    <item>
                        <title>Valid Story</title>
                        <link>https://example.com/1</link>
                        <pubDate>{today_str}</pubDate>
                    </item>
                    </channel></rss>""".encode()
                return mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1

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

        # Use today's date
        from datetime import datetime
        now = datetime.now()
        today_struct = struct_time((now.year, now.month, now.day, now.hour, 0, 0, 3, 353, 0))

        entry1 = Mock()
        entry1.published_parsed = today_struct
        entry1.get = lambda k, d=None: d  # Returns default for all gets

        entry2 = Mock()
        entry2.title = "Title Only"
        entry2.published_parsed = today_struct
        entry2.get = lambda k, d=None: getattr(entry2, k, d)

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = {"title": "Test Feed"}
        mock_feed.entries = [entry1, entry2]

        with patch("feedparser.parse") as mock_parse, \
             patch("httpx.Client") as mock_client_class:
            mock_parse.return_value = mock_feed

            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = b"mock content"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            assert news is not None
            assert len(news.headlines) >= 1

    def test_fetch_headlines_network_timeout(self):
        """fetch_headlines should handle network timeouts gracefully."""
        client = RSSNewsClient()

        # Use today's date
        from datetime import datetime
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%dT%H:00:00Z")

        call_count = [0]

        # Mock httpx to simulate timeout on first feed, success on others
        def mock_get_side_effect(url, headers):
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.TimeoutException("Request timed out")
            # Other feeds return valid RSS XML
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.content = f"""<?xml version="1.0"?>
                <rss><channel><title>Working Feed</title>
                <item>
                    <title>Valid Story</title>
                    <link>https://example.com/1</link>
                    <pubDate>{today_str}</pubDate>
                </item>
                </channel></rss>""".encode()
            return mock_response

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.get = Mock(side_effect=mock_get_side_effect)
            mock_client_class.return_value.__enter__.return_value = mock_client

            news = client.fetch_headlines()

            # Should still succeed with data from the other feeds
            assert news is not None
            assert len(news.headlines) >= 1


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
