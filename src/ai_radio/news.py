"""News headlines fetching from RSS feeds.

Aggregates recent headlines from configured RSS feeds.
Handles feed parsing errors and deduplicates entries.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import feedparser
import httpx

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class NewsHeadline:
    """Single news headline with metadata."""

    title: str
    source: str  # Feed title/source name
    link: str
    published: Optional[datetime] = None


@dataclass
class NewsData:
    """Collection of news headlines from multiple sources."""

    headlines: list[NewsHeadline]
    timestamp: datetime
    source_count: int  # Number of feeds successfully fetched


class RSSNewsClient:
    """RSS news feed aggregator.

    Fetches headlines from configured RSS feeds and deduplicates entries.
    Handles feed parsing errors gracefully.
    """

    def __init__(self):
        """Initialize RSS client with configured feeds."""
        self.feed_urls = config.news_rss_feeds
        self.max_headlines_per_feed = 5
        self.timeout = 10.0
        self.user_agent = "AIRadioStation/1.0 (https://radio.clintecker.com)"

    def fetch_headlines(self) -> Optional[NewsData]:
        """Fetch recent headlines from all configured RSS feeds.

        Returns:
            NewsData with aggregated headlines, or None if all feeds fail.
        """
        all_headlines: list[NewsHeadline] = []
        successful_feeds = 0

        for feed_url in self.feed_urls:
            try:
                logger.info(f"Fetching RSS feed: {feed_url}")

                # Fetch with explicit timeout using httpx
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                    response = client.get(
                        feed_url,
                        headers={"User-Agent": self.user_agent}
                    )
                    response.raise_for_status()

                # Parse the fetched content
                feed = feedparser.parse(response.content)

                if feed.bozo:
                    # Feed has parsing errors
                    logger.warning(f"RSS feed parsing error for {feed_url}: {feed.bozo_exception}")
                    continue

                if not feed.entries:
                    logger.warning(f"RSS feed has no entries: {feed_url}")
                    continue

                feed_title = feed.feed.get("title", "Unknown Source")
                successful_feeds += 1

                # Extract headlines (limited per feed)
                for entry in feed.entries[: self.max_headlines_per_feed]:
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            pass

                    headline = NewsHeadline(
                        title=entry.get("title", "Untitled"),
                        source=feed_title,
                        link=entry.get("link", ""),
                        published=published,
                    )
                    all_headlines.append(headline)

                logger.info(f"Fetched {len(feed.entries[:self.max_headlines_per_feed])} headlines from {feed_title}")

            except Exception as e:
                logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
                continue

        if not all_headlines:
            logger.error("No headlines fetched from any RSS feed")
            return None

        # Deduplicate by title (case-insensitive)
        seen_titles = set()
        unique_headlines = []
        for headline in all_headlines:
            title_lower = headline.title.lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_headlines.append(headline)

        logger.info(f"Aggregated {len(unique_headlines)} unique headlines from {successful_feeds} feeds")

        return NewsData(
            headlines=unique_headlines,
            timestamp=datetime.now(),
            source_count=successful_feeds,
        )


def get_news() -> Optional[NewsData]:
    """Convenience function to fetch news headlines.

    Returns:
        NewsData with headlines, or None if fetch fails.
    """
    client = RSSNewsClient()
    return client.fetch_headlines()
