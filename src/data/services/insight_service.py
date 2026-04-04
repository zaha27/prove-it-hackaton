"""Insight service for generating AI-powered commodity analysis."""

from datetime import datetime, timedelta
from typing import Any

from src.data.clients.deepseek_client import DeepSeekClient
from src.data.models.insight import AIInsight
from src.data.services.news_service import NewsService
from src.data.services.price_service import PriceService


class InsightService:
    """Service for generating AI insights on commodities."""

    def __init__(self) -> None:
        """Initialize the insight service."""
        self.llm_client = DeepSeekClient()
        self.price_service = PriceService()
        self.news_service = NewsService()

        # Simple cache for insights
        self._cache: dict[str, tuple[AIInsight, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour

    def _get_cache_key(self, commodity: str) -> str:
        """Generate cache key."""
        return f"insight:{commodity}"

    def _get_cached(self, cache_key: str) -> AIInsight | None:
        """Get cached insight if not expired."""
        if cache_key not in self._cache:
            return None

        insight, timestamp = self._cache[cache_key]
        if datetime.utcnow() - timestamp > self._cache_ttl:
            del self._cache[cache_key]
            return None

        return insight

    def generate_insight(
        self,
        commodity: str,
        use_cache: bool = True,
    ) -> AIInsight:
        """Generate AI insight for a commodity.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            use_cache: Whether to use cached insight

        Returns:
            AIInsight object
        """
        cache_key = self._get_cache_key(commodity)

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        # Gather data
        price_data = self.price_service.get_latest_price(commodity)
        price_summary = self.price_service.get_price_summary(commodity)

        # Add 30-day range to price data
        price_data["high_30d"] = price_summary.get("high_30d", 0)
        price_data["low_30d"] = price_summary.get("low_30d", 0)

        # Get news summary
        news_summary = self.news_service.get_news_summary(commodity, max_articles=5)

        # Generate insight via LLM
        insight = self.llm_client.generate_insight(
            commodity=commodity,
            price_data=price_data,
            news_summary=news_summary,
        )

        # Cache the result
        self._cache[cache_key] = (insight, datetime.utcnow())

        return insight

    def generate_insight_with_context(
        self,
        commodity: str,
        custom_context: str = "",
    ) -> AIInsight:
        """Generate insight with additional custom context.

        Args:
            commodity: Commodity symbol
            custom_context: Additional context to include

        Returns:
            AIInsight object
        """
        # Get base data
        price_data = self.price_service.get_latest_price(commodity)
        news_summary = self.news_service.get_news_summary(commodity, max_articles=5)

        # Append custom context
        if custom_context:
            news_summary += f"\n\nAdditional Context:\n{custom_context}"

        # Generate insight
        insight = self.llm_client.generate_insight(
            commodity=commodity,
            price_data=price_data,
            news_summary=news_summary,
        )

        return insight

    def compare_commodities(self, commodities: list[str]) -> dict[str, Any]:
        """Generate comparative analysis for multiple commodities.

        Args:
            commodities: List of commodity symbols

        Returns:
            Dictionary with comparative analysis
        """
        insights = {}
        price_data = {}

        for commodity in commodities:
            insights[commodity] = self.generate_insight(commodity)
            price_data[commodity] = self.price_service.get_latest_price(commodity)

        # Determine relative strength
        best_performer = max(
            commodities,
            key=lambda c: price_data[c].get("change_24h", 0),
        )
        worst_performer = min(
            commodities,
            key=lambda c: price_data[c].get("change_24h", 0),
        )

        return {
            "commodities": commodities,
            "insights": insights,
            "price_data": price_data,
            "best_performer": best_performer,
            "worst_performer": worst_performer,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_insight_history(
        self,
        commodity: str,
        hours: int = 24,
    ) -> list[AIInsight]:
        """Get cached insights for a commodity.

        Args:
            commodity: Commodity symbol
            hours: Number of hours to look back

        Returns:
            List of AIInsight objects
        """
        # For now, return current cached insight if available
        cache_key = self._get_cache_key(commodity)
        if cache_key in self._cache:
            insight, timestamp = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(hours=hours):
                return [insight]
        return []

    def clear_cache(self) -> None:
        """Clear the insight cache."""
        self._cache.clear()

    def init_services(self) -> None:
        """Initialize dependent services."""
        self.news_service.init_vector_store()
