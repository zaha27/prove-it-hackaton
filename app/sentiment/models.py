"""Sentiment module Pydantic models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from src.data.models.news import NewsArticle


class NewsResponse(BaseModel):
    """News response model."""

    commodity: str = Field(..., description="Commodity symbol")
    articles: List[NewsArticle] = Field(..., description="List of news articles")
    total_count: int = Field(..., description="Total number of articles")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "articles": [
                    {
                        "id": "news_001",
                        "title": "Gold Prices Surge Amid Inflation Concerns",
                        "source": "Reuters",
                        "date": "2024-01-15",
                        "content": "Investors flock to gold as inflation data exceeds expectations...",
                        "url": "https://example.com/news/1",
                        "sentiment": "positive",
                        "sentiment_score": 0.75,
                        "commodity": "GOLD",
                        "embedding": [],
                        "fetched_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total_count": 1,
                "fetched_at": "2024-01-15T10:30:00Z",
            }
        }


class SentimentSummary(BaseModel):
    """Sentiment summary model."""

    commodity: str = Field(..., description="Commodity symbol")
    overall_sentiment: str = Field(
        ..., description="Overall sentiment (positive, negative, neutral)"
    )
    sentiment_score: float = Field(
        ..., description="Average sentiment score (-1.0 to 1.0)"
    )
    positive_count: int = Field(..., description="Number of positive articles")
    negative_count: int = Field(..., description="Number of negative articles")
    neutral_count: int = Field(..., description="Number of neutral articles")
    total_articles: int = Field(..., description="Total number of articles analyzed")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "overall_sentiment": "positive",
                "sentiment_score": 0.35,
                "positive_count": 5,
                "negative_count": 2,
                "neutral_count": 3,
                "total_articles": 10,
                "fetched_at": "2024-01-15T10:30:00Z",
            }
        }
