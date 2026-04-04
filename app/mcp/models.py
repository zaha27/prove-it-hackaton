"""MCP module Pydantic models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from src.data.models.insight import AIInsight


class MCPContextRequest(BaseModel):
    """MCP context request model."""

    query: str = Field(..., description="Search query for context")
    commodity: Optional[str] = Field(
        None, description="Commodity symbol for context filtering"
    )
    max_tokens: int = Field(
        1000, description="Maximum tokens for response", ge=100, le=4000
    )
    temperature: float = Field(0.3, description="Sampling temperature", ge=0.0, le=2.0)


class MCPContextResponse(BaseModel):
    """MCP context response model."""

    query: str = Field(..., description="Original query")
    commodity: Optional[str] = Field(None, description="Commodity symbol")
    context: str = Field(..., description="Retrieved context")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source documents"
    )
    token_count: int = Field(..., description="Number of tokens used")
    model: str = Field(..., description="Model used for generation")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when context was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "gold price inflation impact",
                "commodity": "GOLD",
                "context": "Gold prices are rising due to inflation concerns and geopolitical tensions...",
                "sources": [
                    {
                        "title": "Inflation Data Exceeds Expectations",
                        "source": "Reuters",
                        "date": "2024-01-15",
                        "url": "https://example.com/news/1",
                    }
                ],
                "token_count": 150,
                "model": "gemini-pro",
                "fetched_at": "2024-01-15T10:30:00Z",
            }
        }


class MCPInsightRequest(BaseModel):
    """MCP insight request model."""

    commodity: str = Field(..., description="Commodity symbol")
    price_data: Dict[str, Any] = Field(..., description="Price data dictionary")
    news_summary: str = Field(..., description="News summary")
    use_mcp: bool = Field(True, description="Whether to use MCP for enhanced context")
    mcp_query: Optional[str] = Field(None, description="Custom MCP query for context")


class MCPInsightResponse(BaseModel):
    """MCP insight response model."""

    commodity: str = Field(..., description="Commodity symbol")
    insight: AIInsight = Field(..., description="Generated AI insight")
    mcp_context: Optional[MCPContextResponse] = Field(
        None, description="MCP context used"
    )
    use_mcp: bool = Field(..., description="Whether MCP was used")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when insight was generated",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "insight": {
                    "commodity": "GOLD",
                    "summary": "Gold prices are trending upward due to inflation concerns",
                    "key_factors": [
                        "Inflation data",
                        "Geopolitical tensions",
                        "USD weakness",
                    ],
                    "price_outlook": "Bullish with support at $2000 and resistance at $2050",
                    "recommendation": "Consider long positions with stop-loss at $1980",
                    "sentiment": "bullish",
                    "confidence": 0.85,
                    "model": "deepseek-chat",
                },
                "mcp_context": {
                    "query": "gold price inflation impact",
                    "commodity": "GOLD",
                    "context": "Gold prices are rising due to inflation concerns and geopolitical tensions...",
                    "sources": [],
                    "token_count": 150,
                    "model": "gemini-pro",
                    "fetched_at": "2024-01-15T10:30:00Z",
                },
                "use_mcp": True,
                "fetched_at": "2024-01-15T10:30:00Z",
            }
        }
