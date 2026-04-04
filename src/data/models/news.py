"""News article model definitions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """News article with sentiment and embedding."""

    id: str = Field(..., description="Unique article ID")
    title: str = Field(..., description="Article title")
    source: str = Field(..., description="News source")
    date: str = Field(..., description="Publication date (YYYY-MM-DD)")
    content: str = Field(default="", description="Article content/summary")
    url: str = Field(default="", description="Article URL")
    sentiment: str = Field(
        default="neutral", description="Sentiment: positive, negative, neutral"
    )
    sentiment_score: float = Field(
        default=0.0, description="Sentiment score (-1.0 to 1.0)"
    )
    commodity: str = Field(
        default="", description="Related commodity symbol"
    )
    embedding: list[float] = Field(
        default_factory=list, description="Vector embedding"
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when article was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "news_001",
                "title": "Gold Prices Surge Amid Inflation Concerns",
                "source": "Reuters",
                "date": "2024-01-15",
                "content": "Investors flock to gold as inflation data exceeds expectations...",
                "url": "https://example.com/news/1",
                "sentiment": "positive",
                "sentiment_score": 0.75,
                "commodity": "GOLD",
            }
        }

    def to_qdrant_payload(self) -> dict[str, Any]:
        """Convert to Qdrant payload format."""
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "date": self.date,
            "content": self.content,
            "url": self.url,
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "commodity": self.commodity,
            "fetched_at": self.fetched_at.isoformat(),
        }

    @classmethod
    def from_qdrant_payload(
        cls, payload: dict[str, Any], embedding: list[float]
    ) -> "NewsArticle":
        """Create from Qdrant payload."""
        return cls(
            id=payload["id"],
            title=payload["title"],
            source=payload["source"],
            date=payload["date"],
            content=payload.get("content", ""),
            url=payload.get("url", ""),
            sentiment=payload.get("sentiment", "neutral"),
            sentiment_score=payload.get("sentiment_score", 0.0),
            commodity=payload.get("commodity", ""),
            embedding=embedding,
            fetched_at=datetime.fromisoformat(payload["fetched_at"]),
        )
