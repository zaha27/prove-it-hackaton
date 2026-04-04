"""Public API for the data module.

This module exposes the main functions that the UI layer (Dev 2) will use
to interact with the backend data and AI services.
"""

from src.data.models.insight import AIInsight
from src.data.models.news import NewsArticle
from src.data.models.price import PriceData
from src.data.services.insight_service import InsightService
from src.data.services.news_service import NewsService
from src.data.services.price_service import PriceService

# Singleton service instances
_price_service: PriceService | None = None
_news_service: NewsService | None = None
_insight_service: InsightService | None = None


def _get_price_service() -> PriceService:
    """Get or create the price service singleton."""
    global _price_service
    if _price_service is None:
        _price_service = PriceService()
    return _price_service


def _get_news_service() -> NewsService:
    """Get or create the news service singleton."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service


def _get_insight_service() -> InsightService:
    """Get or create the insight service singleton."""
    global _insight_service
    if _insight_service is None:
        _insight_service = InsightService()
    return _insight_service


def get_price_data(
    commodity: str,
    period: str = "1mo",
    interval: str = "1d",
) -> PriceData:
    """Get OHLCV price data for a commodity.

    This is the main function Dev 2 will call to get price chart data.

    Args:
        commodity: Commodity symbol (e.g., "GOLD", "OIL")
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y)
        interval: Data interval (1d, 1h, etc.)

    Returns:
        PriceData object with OHLCV arrays

    Example:
        >>> data = get_price_data("GOLD", period="1mo")
        >>> print(f"Latest price: ${data.close[-1]}")
    """
    service = _get_price_service()
    return service.get_price_data(commodity, period, interval)


def get_news(
    commodity: str,
    days: int = 7,
    limit: int = 20,
) -> list[NewsArticle]:
    """Get news articles for a commodity.

    This function fetches recent news articles related to the commodity,
    including sentiment analysis.

    Args:
        commodity: Commodity symbol (e.g., "GOLD", "OIL")
        days: Number of days to look back
        limit: Maximum number of articles to return

    Returns:
        List of NewsArticle objects with sentiment

    Example:
        >>> news = get_news("GOLD", days=3, limit=5)
        >>> for article in news:
        ...     print(f"{article.title} ({article.sentiment})")
    """
    service = _get_news_service()
    return service.get_news_for_commodity(commodity, days, limit)


def get_ai_insight(commodity: str) -> AIInsight:
    """Get AI-generated insight for a commodity.

    This is the main AI function that combines price data and news
    to generate a comprehensive analysis using DeepSeek V3.2.

    Args:
        commodity: Commodity symbol (e.g., "GOLD", "OIL")

    Returns:
        AIInsight object with analysis, factors, outlook, and recommendation

    Example:
        >>> insight = get_ai_insight("GOLD")
        >>> print(insight.summary)
        >>> print(f"Sentiment: {insight.sentiment}")
        >>> print(insight.to_markdown())  # For display
    """
    service = _get_insight_service()
    return service.generate_insight(commodity)


def search_news(
    query: str,
    commodity: str | None = None,
    top_k: int = 5,
) -> list[NewsArticle]:
    """Search for news articles by semantic similarity.

    Uses vector embeddings to find news articles relevant to the query.

    Args:
        query: Search query string
        commodity: Optional commodity filter (e.g., "GOLD", "OIL")
        top_k: Number of results to return

    Returns:
        List of relevant NewsArticle objects

    Example:
        >>> results = search_news("inflation impact", commodity="GOLD")
        >>> for article in results:
        ...     print(f"{article.title} - {article.source}")
    """
    service = _get_news_service()
    return service.search_relevant_news(query, commodity, top_k)


def init_backend() -> None:
    """Initialize the backend services.

    This should be called once at application startup to initialize
    the vector store and other dependencies.

    Example:
        >>> from src.data.api import init_backend
        >>> init_backend()
    """
    service = _get_insight_service()
    service.init_services()


def clear_caches() -> None:
    """Clear all service caches.

    Useful for forcing fresh data fetches.

    Example:
        >>> from src.data.api import clear_caches
        >>> clear_caches()
    """
    if _price_service:
        _price_service.clear_cache()
    if _insight_service:
        _insight_service.clear_cache()


# Commodity constants for convenience
# Commodity constants for convenience
SUPPORTED_COMMODITIES = [
    "GOLD", 
    "SILVER", 
    "OIL", 
    "NATURAL_GAS", 
    "WHEAT", 
    "COPPER"
]


def get_supported_commodities() -> list[str]:
    """Get list of supported commodity symbols.

    Returns:
        List of supported commodity symbols
    """
    return SUPPORTED_COMMODITIES.copy()


def is_commodity_supported(commodity: str) -> bool:
    """Check if a commodity is supported.

    Args:
        commodity: Commodity symbol to check

    Returns:
        True if supported, False otherwise
    """
    return commodity.upper() in SUPPORTED_COMMODITIES
