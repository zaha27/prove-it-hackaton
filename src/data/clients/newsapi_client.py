"""NewsAPI client for fetching news articles."""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from newsapi import NewsApiClient

from src.data.config import config
from src.data.models.news import NewsArticle


class NewsAPIClient:
    """Client for fetching news from NewsAPI."""

    def __init__(self) -> None:
        """Initialize the NewsAPI client."""
        self.api_key = config.newsapi_key
        self.client = NewsApiClient(api_key=self.api_key) if self.api_key else None

        # Commodity to search query mapping
        self.commodity_queries: dict[str, str] = {
            "GOLD": "gold price OR gold futures OR XAU",
            "OIL": "oil price OR crude oil OR WTI OR Brent OR petroleum",
        }

    def _generate_id(self, title: str, date: str) -> str:
        """Generate a unique ID for an article."""
        content = f"{title}:{date}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _analyze_sentiment(self, text: str) -> tuple[str, float]:
        """Simple keyword-based sentiment analysis.

        Returns:
            Tuple of (sentiment_label, sentiment_score)
        """
        text_lower = text.lower()

        positive_words = [
            "surge", "rise", "rally", "gain", "up", "higher", "bullish",
            "boost", "strong", "growth", "increase", "soar", "jump",
            "positive", "optimistic", "recovery", "breakthrough",
        ]
        negative_words = [
            "fall", "drop", "decline", "crash", "down", "lower", "bearish",
            "plunge", "weak", "loss", "decrease", "tumble", "slump",
            "negative", "pessimistic", "crisis", "concern", "worry",
        ]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return "neutral", 0.0

        score = (pos_count - neg_count) / total

        if score > 0.2:
            return "positive", min(score, 1.0)
        elif score < -0.2:
            return "negative", max(score, -1.0)
        else:
            return "neutral", score

    def fetch_news(
        self,
        commodity: str,
        days_back: int = 7,
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Fetch news articles for a commodity.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            days_back: Number of days to look back
            page_size: Maximum number of articles to fetch

        Returns:
            List of NewsArticle objects

        Raises:
            ValueError: If commodity is not supported or API key is missing
        """
        if not self.client:
            raise ValueError("NewsAPI key not configured")

        if commodity not in self.commodity_queries:
            raise ValueError(
                f"Unsupported commodity: {commodity}. "
                f"Supported: {list(self.commodity_queries.keys())}"
            )

        query = self.commodity_queries[commodity]
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        try:
            response = self.client.get_everything(
                q=query,
                from_param=from_date,
                to=to_date,
                language="en",
                sort_by="relevancy",
                page_size=page_size,
            )

            articles = []
            for article in response.get("articles", []):
                title = article.get("title", "")
                description = article.get("description", "") or ""
                content = article.get("content", "") or ""

                # Combine text for sentiment analysis
                full_text = f"{title} {description} {content}"
                sentiment, sentiment_score = self._analyze_sentiment(full_text)

                # Parse date
                published_at = article.get("publishedAt", "")
                if published_at:
                    date_str = published_at[:10]  # Extract YYYY-MM-DD
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")

                news_article = NewsArticle(
                    id=self._generate_id(title, date_str),
                    title=title,
                    source=article.get("source", {}).get("name", "Unknown"),
                    date=date_str,
                    content=description or content,
                    url=article.get("url", ""),
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    commodity=commodity,
                )
                articles.append(news_article)

            return articles

        except Exception as e:
            raise ValueError(f"Failed to fetch news for {commodity}: {e}") from e

    def fetch_top_headlines(
        self, commodity: str, page_size: int = 10
    ) -> list[NewsArticle]:
        """Fetch top headlines for a commodity.

        Args:
            commodity: Commodity symbol
            page_size: Number of headlines to fetch

        Returns:
            List of NewsArticle objects
        """
        if not self.client:
            raise ValueError("NewsAPI key not configured")

        if commodity not in self.commodity_queries:
            raise ValueError(f"Unsupported commodity: {commodity}")

        query = self.commodity_queries[commodity]

        try:
            response = self.client.get_top_headlines(
                q=query,
                language="en",
                page_size=page_size,
            )

            articles = []
            for article in response.get("articles", []):
                title = article.get("title", "")
                description = article.get("description", "") or ""
                content = article.get("content", "") or ""
                full_text = f"{title} {description} {content}"
                sentiment, sentiment_score = self._analyze_sentiment(full_text)

                published_at = article.get("publishedAt", "")
                date_str = published_at[:10] if published_at else datetime.now().strftime("%Y-%m-%d")

                news_article = NewsArticle(
                    id=self._generate_id(title, date_str),
                    title=title,
                    source=article.get("source", {}).get("name", "Unknown"),
                    date=date_str,
                    content=description or content,
                    url=article.get("url", ""),
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    commodity=commodity,
                )
                articles.append(news_article)

            return articles

        except Exception as e:
            raise ValueError(f"Failed to fetch headlines for {commodity}: {e}") from e
