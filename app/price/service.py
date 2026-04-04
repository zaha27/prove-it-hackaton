"""Price service module."""

from datetime import datetime
from typing import List, Optional

from src.data.services.price_service import PriceService as BasePriceService
from src.data.models.price import PriceData as BasePriceData
from app.price.models import PriceDataResponse, LatestPriceResponse, PricePoint


class PriceService:
    """Price service for API endpoints."""

    def __init__(self):
        """Initialize the price service."""
        self._base_service = BasePriceService()

    async def get_price_data(
        self, commodity: str, period: str = "1mo", interval: str = "1d"
    ) -> PriceDataResponse:
        """
        Get OHLCV price data for a commodity.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y)
            interval: Data interval (1d, 1h, etc.)

        Returns:
            PriceDataResponse object
        """
        # Run in thread pool since yfinance is synchronous
        import asyncio

        loop = asyncio.get_event_loop()
        base_data: BasePriceData = await loop.run_in_executor(
            None, self._base_service.get_price_data, commodity, period, interval
        )

        # Convert to API model
        price_points = []
        for i in range(len(base_data.dates)):
            price_points.append(
                PricePoint(
                    timestamp=datetime.strptime(base_data.dates[i], "%Y-%m-%d"),
                    open=base_data.open[i],
                    high=base_data.high[i],
                    low=base_data.low[i],
                    close=base_data.close[i],
                    volume=base_data.volume[i],
                )
            )

        return PriceDataResponse(
            commodity=base_data.commodity,
            data=price_points,
            fetched_at=base_data.fetched_at,
        )

    async def get_latest_price(self, commodity: str) -> LatestPriceResponse:
        """
        Get latest price information for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            LatestPriceResponse object
        """
        import asyncio

        loop = asyncio.get_event_loop()
        base_data: dict = await loop.run_in_executor(
            None, self._base_service.get_latest_price, commodity
        )

        # Get additional 24h high/low from price data
        price_summary: dict = await loop.run_in_executor(
            None, self._base_service.get_price_summary, commodity
        )

        return LatestPriceResponse(
            commodity=commodity,
            current_price=base_data["current_price"],
            change_24h=base_data["change_24h"],
            change_24h_abs=base_data["current_price"] * (base_data["change_24h"] / 100),
            high_24h=price_summary.get("high_30d"),  # Using 30d high as approximation
            low_24h=price_summary.get("low_30d"),  # Using 30d low as approximation
            fetched_at=datetime.utcnow(),
        )
