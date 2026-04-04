"""Price service for fetching and caching price data."""

from datetime import datetime, timedelta
from typing import Any

from src.data.clients.yfinance_client import YFinanceClient
from src.data.models.price import PriceData


class PriceService:
    """Service for managing commodity price data."""

    def __init__(self) -> None:
        """Initialize the price service."""
        self.client = YFinanceClient()
        # Simple in-memory cache
        self._cache: dict[str, tuple[PriceData, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def _get_cache_key(self, commodity: str, period: str, interval: str) -> str:
        """Generate cache key."""
        return f"{commodity}:{period}:{interval}"

    def _get_cached(self, cache_key: str) -> PriceData | None:
        """Get cached data if not expired."""
        if cache_key not in self._cache:
            return None

        data, timestamp = self._cache[cache_key]
        if datetime.utcnow() - timestamp > self._cache_ttl:
            del self._cache[cache_key]
            return None

        return data

    def get_price_data(
        self,
        commodity: str,
        period: str = "1mo",
        interval: str = "1d",
        use_cache: bool = True,
    ) -> PriceData:
        """Get price data for a commodity.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            period: Data period (1d, 5d, 1mo, etc.)
            interval: Data interval (1d, 1h, etc.)
            use_cache: Whether to use cached data

        Returns:
            PriceData object
        """
        cache_key = self._get_cache_key(commodity, period, interval)

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        # Fetch fresh data
        data = self.client.fetch_ohlcv(commodity, period, interval)

        # Cache the result
        self._cache[cache_key] = (data, datetime.utcnow())

        return data

    def get_latest_price(self, commodity: str) -> dict[str, Any]:
        """Get latest price information for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            Dictionary with price information
        """
        price, change_pct = self.client.fetch_latest_price(commodity)

        # Get trend
        data = self.get_price_data(commodity, period="5d")
        trend = "neutral"
        if len(data.close) >= 3:
            if data.close[-1] > data.close[-3]:
                trend = "up"
            elif data.close[-1] < data.close[-3]:
                trend = "down"

        return {
            "commodity": commodity,
            "current_price": price,
            "change_24h": change_pct,
            "trend": trend,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_price_summary(self, commodity: str) -> dict[str, Any]:
        """Get comprehensive price summary.

        Args:
            commodity: Commodity symbol

        Returns:
            Dictionary with price summary
        """
        data = self.get_price_data(commodity, period="1mo")

        if not data.close:
            return {"error": "No price data available"}

        current = data.close[-1]
        high_30d = max(data.high) if data.high else current
        low_30d = min(data.low) if data.low else current
        avg_volume = sum(data.volume) / len(data.volume) if data.volume else 0

        # Calculate 7-day and 30-day changes
        change_7d = 0.0
        change_30d = 0.0

        if len(data.close) > 7:
            change_7d = ((current - data.close[-7]) / data.close[-7]) * 100

        if len(data.close) > 1:
            change_30d = ((current - data.close[0]) / data.close[0]) * 100

        return {
            "commodity": commodity,
            "current_price": current,
            "high_30d": high_30d,
            "low_30d": low_30d,
            "change_7d_pct": change_7d,
            "change_30d_pct": change_30d,
            "avg_volume_30d": int(avg_volume),
            "price_range": f"${low_30d:,.2f} - ${high_30d:,.2f}",
        }

    def clear_cache(self) -> None:
        """Clear the price cache."""
        self._cache.clear()
