"""Unit tests for sentiment service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.sentiment.service import SentimentService
from app.sentiment.models import NewsResponse, SentimentSummary
from src.data.models.news import NewsArticle


@pytest.fixture
def sentiment_service():
    """Create sentiment service instance."""
    return SentimentService()


@pytest.fixture
def mock_articles():
    """Mock news articles."""
    return [
        NewsArticle(
            id="news_1",
            title="Gold Prices Rise",
            source="Reuters",
            date="2024-01-01",
            content="Gold prices are rising...",
            url="https://example.com/1",
            sentiment="positive",
            sentiment_score=0.5,
            commodity="GOLD",
            fetched_at=datetime.utcnow(),
        ),
        NewsArticle(
            id="news_2",
            title="Market Stable",
            source="Bloomberg",
            date="2024-01-02",
            content="Markets are stable...",
            url="https://example.com/2",
            sentiment="neutral",
            sentiment_score=0.0,
            commodity="GOLD",
            fetched_at=datetime.utcnow(),
        ),
    ]


class TestSentimentService:
    """Test cases for SentimentService."""

    @pytest.mark.asyncio
    async def test_get_news_success(self, sentiment_service, mock_articles):
        """Test successful news retrieval."""
        with patch.object(
            sentiment_service._base_service,
            "get_news_for_commodity",
            return_value=mock_articles,
        ):
            result = await sentiment_service.get_news("GOLD", days=7, limit=10)

            assert isinstance(result, NewsResponse)
            assert result.commodity == "GOLD"
            assert result.total_count == 2
            assert len(result.articles) == 2
            assert result.articles[0].sentiment == "positive"

    @pytest.mark.asyncio
    async def test_get_news_empty(self, sentiment_service):
        """Test news retrieval with no articles."""
        with patch.object(
            sentiment_service._base_service, "get_news_for_commodity", return_value=[]
        ):
            result = await sentiment_service.get_news("GOLD")

            assert result.total_count == 0
            assert len(result.articles) == 0

    @pytest.mark.asyncio
    async def test_get_sentiment_summary(self, sentiment_service, mock_articles):
        """Test sentiment summary generation."""
        with patch.object(
            sentiment_service._base_service,
            "get_news_for_commodity",
            return_value=mock_articles,
        ):
            result = await sentiment_service.get_sentiment_summary("GOLD")

            assert isinstance(result, SentimentSummary)
            assert result.commodity == "GOLD"
            assert result.total_articles == 2
            assert result.positive_count == 1
            assert result.neutral_count == 1
            assert result.negative_count == 0
            # Average sentiment: (0.5 + 0.0) / 2 = 0.25
            assert abs(result.sentiment_score - 0.25) < 0.001
            assert result.overall_sentiment == "positive"  # Since 0.25 > 0.1

    @pytest.mark.asyncio
    async def test_get_sentiment_summary_no_articles(self, sentiment_service):
        """Test sentiment summary with no articles."""
        with patch.object(
            sentiment_service._base_service, "get_news_for_commodity", return_value=[]
        ):
            result = await sentiment_service.get_sentiment_summary("GOLD")

            assert result.total_articles == 0
            assert result.positive_count == 0
            assert result.negative_count == 0
            assert result.neutral_count == 0
            assert result.sentiment_score == 0.0
            assert result.overall_sentiment == "neutral"
