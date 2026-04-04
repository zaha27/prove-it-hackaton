"""Dependency injection module."""

from functools import lru_cache

from src.data.services.price_service import PriceService
from src.data.services.news_service import NewsService
from src.data.services.insight_service import InsightService
from src.data.clients.deepseek_client import DeepSeekClient

from app.price.service import PriceService as PriceAPIService
from app.sentiment.service import SentimentService
from app.change.service import ChangeService
from app.mcp.service import MCPService
from app.macro.service import MacroService


@lru_cache()
def get_price_service():
    """Get price service instance."""
    return PriceAPIService()


@lru_cache()
def get_sentiment_service():
    """Get sentiment service instance."""
    return SentimentService()


@lru_cache()
def get_change_service():
    """Get change service instance."""
    return ChangeService()


@lru_cache()
def get_mcp_service():
    """Get MCP service instance."""
    return MCPService()


@lru_cache()
def get_macro_service():
    """Get macro service instance."""
    return MacroService()
