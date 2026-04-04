"""Change service module."""

from datetime import datetime
from typing import Optional

from src.data.services.price_service import PriceService as BasePriceService
from app.change.models import Change24hResponse, ChangeComparisonResponse


class ChangeService:
    """Change service for API endpoints."""

    def __init__(self):
        """Initialize the change service."""
        self._base_service = BasePriceService()

    async def get_24h_change(self, commodity: str) -> Change24hResponse:
        """
        Get 24-hour price change for a commodity.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")

        Returns:
            Change24hResponse object
        """
        import asyncio

        loop = asyncio.get_event_loop()
        base_data: dict = await loop.run_in_executor(
            None, self._base_service.get_latest_price, commodity
        )

        # Determine direction
        change_pct = base_data["change_24h"]
        if change_pct > 0.1:
            direction = "up"
        elif change_pct < -0.1:
            direction = "down"
        else:
            direction = "neutral"

        return Change24hResponse(
            commodity=commodity.upper(),
            current_price=base_data["current_price"],
            change_24h=base_data["change_24h"],
            change_24h_abs=base_data["current_price"] * (base_data["change_24h"] / 100),
            change_24h_direction=direction,
            fetched_at=datetime.utcnow(),
        )

    async def compare_24h_change(
        self, base_commodity: str, target_commodity: str
    ) -> ChangeComparisonResponse:
        """
        Compare 24-hour price changes between two commodities.

        Args:
            base_commodity: Base commodity symbol
            target_commodity: Target commodity symbol

        Returns:
            ChangeComparisonResponse object
        """
        import asyncio

        loop = asyncio.get_event_loop()

        base_data: dict = await loop.run_in_executor(
            None, self._base_service.get_latest_price, base_commodity
        )
        target_data: dict = await loop.run_in_executor(
            None, self._base_service.get_latest_price, target_commodity
        )

        base_change = base_data["change_24h"]
        target_change = target_data["change_24h"]
        change_difference = target_change - base_change

        return ChangeComparisonResponse(
            base_commodity=base_commodity.upper(),
            target_commodity=target_commodity.upper(),
            base_change_24h=base_change,
            target_change_24h=target_change,
            change_difference=change_difference,
            fetched_at=datetime.utcnow(),
        )
