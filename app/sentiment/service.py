"""Sentiment service module."""

from datetime import datetime
from typing import List

from src.data.services.news_service import NewsService as BaseNewsService
from src.data.models.news import NewsArticle
from app.sentiment.models import NewsResponse, SentimentSummary


class SentimentService:
    """Sentiment service for API endpoints."""

    def __init__(self):
        """Initialize the sentiment service."""
        self._base_service = BaseNewsService()

    async def get_news(
        self, commodity: str, days: int = 7, limit: int = 20
    ) -> NewsResponse:
        """
        Get news articles for a commodity.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")
            days: Number of days to look back
            limit: Maximum number of articles to return

        Returns:
            NewsResponse object
        """
        import asyncio

        loop = asyncio.get_event_loop()
        articles: List[NewsArticle] = await loop.run_in_executor(
            None, self._base_service.get_news_for_commodity, commodity, days, limit
        )

        return NewsResponse(
            commodity=commodity.upper(),
            articles=articles,
            total_count=len(articles),
            fetched_at=datetime.utcnow(),
        )

    async def get_sentiment_summary(
        self, commodity: str, days: int = 7, limit: int = 20
    ) -> SentimentSummary:
        """
        Get sentiment summary for a commodity.

        Args:
            commodity: Commodity symbol
            days: Number of days to look back
            limit: Maximum number of articles to analyze

        Returns:
            SentimentSummary object
        """
        news_response = await self.get_news(commodity, days, limit)
        articles = news_response.articles

        if not articles:
            return SentimentSummary(
                commodity=commodity.upper(),
                overall_sentiment="neutral",
                sentiment_score=0.0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                total_articles=0,
                fetched_at=datetime.utcnow(),
            )

        positive_count = sum(1 for a in articles if a.sentiment == "positive")
        negative_count = sum(1 for a in articles if a.sentiment == "negative")
        neutral_count = sum(1 for a in articles if a.sentiment == "neutral")

        # Calculate average sentiment score
        total_score = sum(a.sentiment_score for a in articles)
        avg_score = total_score / len(articles) if articles else 0.0

        # Determine overall sentiment
        if avg_score > 0.1:
            overall_sentiment = "positive"
        elif avg_score < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"

        return SentimentSummary(
            commodity=commodity.upper(),
            overall_sentiment=overall_sentiment,
            sentiment_score=round(avg_score, 3),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            total_articles=len(articles),
            fetched_at=datetime.utcnow(),
        )
