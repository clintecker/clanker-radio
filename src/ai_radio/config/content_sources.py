"""Content sources configuration."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContentSourcesConfig(BaseSettings):
    """Content sources for news and weather data.

    Environment variables:
        RADIO_NWS_OFFICE: NWS office code
        RADIO_NWS_GRID_X: NWS grid X coordinate
        RADIO_NWS_GRID_Y: NWS grid Y coordinate
        RADIO_NEWS_RSS_FEEDS: Categorized RSS feed URLs (JSON)
        RADIO_HALLUCINATE_NEWS: Generate fake news articles
        RADIO_HALLUCINATION_CHANCE: Probability of hallucinating (0.0-1.0)
        RADIO_HALLUCINATION_KERNELS: Seed topics for fake news (JSON array)
    """

    model_config = SettingsConfigDict(
        env_prefix="RADIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # NWS Weather Configuration
    nws_office: Optional[str] = Field(default=None, description="NWS office code")
    nws_grid_x: Optional[int] = Field(default=None, description="NWS grid X coordinate")
    nws_grid_y: Optional[int] = Field(default=None, description="NWS grid Y coordinate")

    # News RSS Feeds
    news_rss_feeds: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "news": [
                "https://feeds.npr.org/1001/rss.xml",
            ],
        },
        description="Categorized RSS feed URLs for news headlines"
    )

    # Hallucinated news settings
    hallucinate_news: bool = Field(default=False, description="Generate fake news article to mix with real news")
    hallucination_chance: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of hallucinating news (0.0-1.0)")
    hallucination_kernels: list[str] = Field(
        default_factory=list,
        description="Seed topics for hallucinated news stories"
    )
