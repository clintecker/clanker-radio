"""News headlines fetching from RSS feeds.

Aggregates recent headlines from configured RSS feeds.
Handles feed parsing errors and deduplicates entries.
Selects diverse content from multiple categories.
"""

import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import fasteners
import feedparser
import httpx
from anthropic import Anthropic

from .config import config

logger = logging.getLogger(__name__)


def log_hallucinated_headline(headline_text: str) -> None:
    """Log hallucinated headline to avoid future repetition.

    Args:
        headline_text: The generated headline text
    """
    try:
        headlines_file = config.state_path / "recent_hallucinated_headlines.json"
        headlines_file.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file for inter-process synchronization
        lock_file = headlines_file.with_suffix('.lock')
        lock = fasteners.InterProcessLock(lock_file)

        with lock:
            # Load existing headlines
            existing = []
            if headlines_file.exists() and headlines_file.stat().st_size > 0:
                with open(headlines_file, 'r') as f:
                    existing = json.load(f)

            # Add new headline and keep last 30 (roughly 30 hours of history)
            all_headlines = existing + [headline_text]
            recent_headlines = all_headlines[-30:]

            # Save back
            with open(headlines_file, 'w') as f:
                json.dump(recent_headlines, f, indent=2)

        logger.info(f"Logged hallucinated headline for anti-repetition")

    except Exception as e:
        logger.warning(f"Failed to log hallucinated headline: {e}")


def load_recent_hallucinated_headlines() -> list[str]:
    """Load recently used hallucinated headlines to avoid repetition.

    Returns:
        List of recently generated headlines
    """
    try:
        headlines_file = config.state_path / "recent_hallucinated_headlines.json"
        if headlines_file.exists():
            with open(headlines_file, 'r') as f:
                headlines = json.load(f)
            logger.info(f"Loaded {len(headlines)} recent hallucinated headlines to avoid")
            return headlines
        return []
    except Exception as e:
        logger.warning(f"Failed to load recent hallucinated headlines: {e}")
        return []


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
    """RSS news feed aggregator with category-based selection.

    Fetches headlines from categorized RSS feeds, filters for today's news,
    selects 3 random categories, and picks 1 random article from each.
    """

    def __init__(self):
        """Initialize RSS client with configured feeds."""
        self.categorized_feeds = config.news_rss_feeds
        self.max_headlines_per_feed = 10  # Increased to get better today's news coverage
        self.timeout = 10.0
        self.user_agent = "AIRadioStation/1.0 (+https://github.com/your-username/ai-radio-station)"
        self.categories_to_select = 3
        self.articles_per_category = 1

        # Hallucination settings
        if config.llm_api_key and config.hallucinate_news:
            self.claude_client = Anthropic(api_key=config.llm_api_key)
        else:
            self.claude_client = None

    def _generate_hallucinated_headline(self, kernel: str, real_headlines: list[NewsHeadline]) -> Optional[NewsHeadline]:
        """Generate a plausible fake news headline based on a kernel topic.

        Args:
            kernel: Seed topic for hallucination
            real_headlines: Real headlines for context (to make it blend in)

        Returns:
            Hallucinated NewsHeadline, or None if generation fails
        """
        if not self.claude_client:
            return None

        try:
            # Build context from real headlines
            real_context = "\n".join([f"- {h.title}" for h in real_headlines[:3]])

            # Load recent hallucinated headlines to avoid repetition
            recent_headlines = load_recent_hallucinated_headlines()
            avoid_section = ""
            if recent_headlines:
                avoid_section = "\n\nRECENT HEADLINES TO AVOID REPEATING:\n"
                avoid_section += "\n".join([f"- {h}" for h in recent_headlines[-10:]])  # Last 10
                avoid_section += "\n\nDO NOT repeat these topics, themes, or similar phrasing."

            prompt = f"""Generate a single, plausible news headline for {config.station_name} broadcasting from {config.station_location}.

KERNEL/SEED TOPIC: {kernel}

REAL HEADLINES FOR CONTEXT (to match tone and style):
{real_context}{avoid_section}

STATION SETTING: {config.world_setting}
STATION TONE: {config.world_tone}

CRITICAL RULES:
- Generate ONE headline only (10-15 words)
- Make it sound like a real news headline from today
- Fit the station's world setting and tone
- Match the tone and credibility of the real headlines
- Should be indistinguishable from actual news
- NO forced jargon or heavy-handed theme labels
- Specific local references when appropriate
- Sound like it came from AP or Reuters
- MUST be different from recent headlines above

OUTPUT: Just the headline text, nothing else."""

            response = self.claude_client.messages.create(
                model=config.llm_model,
                max_tokens=100,
                temperature=0.9,  # Higher temperature for creativity
                messages=[{"role": "user", "content": prompt}]
            )

            headline_text = response.content[0].text.strip()

            logger.info(f"Hallucinated headline: {headline_text}")

            # Log the headline for future anti-repetition
            log_hallucinated_headline(headline_text)

            return NewsHeadline(
                title=headline_text,
                source="Associated Press",  # Plausible source
                link="",
                published=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Failed to generate hallucinated headline: {e}")
            return None

    def fetch_headlines(self) -> Optional[NewsData]:
        """Fetch headlines with category-based selection.

        Strategy:
        1. Fetch all feeds grouped by category
        2. Filter for today's articles only (published within last 24 hours)
        3. Select 3 random categories
        4. Pick 1 random article from each selected category

        Returns:
            NewsData with selected headlines, or None if all feeds fail.
        """
        # Fetch headlines grouped by category
        headlines_by_category: dict[str, list[NewsHeadline]] = {}
        successful_feeds = 0
        today_cutoff = datetime.now() - timedelta(hours=24)

        for category, feed_urls in self.categorized_feeds.items():
            category_headlines = []

            for feed_url in feed_urls:
                try:
                    logger.info(f"Fetching RSS feed ({category}): {feed_url}")

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

                        # Filter for today's news only
                        if published and published < today_cutoff:
                            continue

                        headline = NewsHeadline(
                            title=entry.get("title", "Untitled"),
                            source=feed_title,
                            link=entry.get("link", ""),
                            published=published,
                        )
                        category_headlines.append(headline)

                    logger.info(f"Fetched {len(category_headlines)} today's headlines from {feed_title}")

                except Exception as e:
                    logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
                    continue

            if category_headlines:
                headlines_by_category[category] = category_headlines

        if not headlines_by_category:
            logger.error("No headlines fetched from any RSS feed")
            return None

        # Select 3 random categories
        available_categories = list(headlines_by_category.keys())
        num_categories = min(self.categories_to_select, len(available_categories))
        selected_categories = random.sample(available_categories, num_categories)

        logger.info(f"Selected categories: {', '.join(selected_categories)}")

        # Pick 1 random article from each selected category
        selected_headlines = []
        for category in selected_categories:
            category_headlines = headlines_by_category[category]
            if category_headlines:
                selected = random.choice(category_headlines)
                selected_headlines.append(selected)
                logger.info(f"  {category}: {selected.title[:60]}...")

        if not selected_headlines:
            logger.error("No headlines selected from categories")
            return None

        # Optionally add hallucinated headline
        if config.hallucinate_news and self.claude_client:
            if random.random() < config.hallucination_chance:
                kernel = random.choice(config.hallucination_kernels)
                logger.info(f"Hallucinating news based on kernel: {kernel}")

                hallucinated = self._generate_hallucinated_headline(kernel, selected_headlines)
                if hallucinated:
                    # Insert at random position to blend in
                    insert_position = random.randint(0, len(selected_headlines))
                    selected_headlines.insert(insert_position, hallucinated)
                    logger.info(f"  Inserted hallucinated headline at position {insert_position}")

        logger.info(f"Final selection: {len(selected_headlines)} headlines from {len(selected_categories)} categories")

        return NewsData(
            headlines=selected_headlines,
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
