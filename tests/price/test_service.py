"""Unit tests for price service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.price.service import PriceService
from app.price.models import PriceDataResponse, LatestPriceResponse, PricePoint


@pytest.fixture
def price_service():
    """Create price service instance."""
    return PriceService()


@pytest.fixture
def mock_price_data():
    """Mock price data from base service."""
    mock_data = MagicMock()
    mock_data.commodity = "GOLD"
    mock_data.dates = ["2024-01-01", "2024-01-02"]
    mock_data.open = [2000.0, 2010.0]
    mock_data.high = [2010.0, 2020.0]
    mock_data.low = [1990.0, 2000.0]
    mock_data.close = [2005.0, 2015.0]
    mock_data.volume = [100000, 120000]
    mock_data.fetched_at = datetime.utcnow()
    return mock_data


@pytest.fixture
def mock_latest_price():
    """Mock latest price data."""
    return {
        "current_price": 2015.0,
        "change_24h": 0.5,
    }


@pytest.fixture
def mock_price_summary():
    """Mock price summary data."""
    return {
        "high_30d": 2020.0,
        "low_30d": 2000.0,
    }


class TestPriceService:
    """Test cases for PriceService."""

    @pytest.mark.asyncio
    async def test_get_price_data_success(self, price_service, mock_price_data):
        """Test successful price data retrieval."""
        with patch.object(
            price_service._base_service, "get_price_data", return_value=mock_price_data
        ):
            result = await price_service.get_price_data("GOLD")

            assert isinstance(result, PriceDataResponse)
            assert result.commodity == "GOLD"
            assert len(result.data) == 2
            assert result.data[0].close == 2005.0
            assert result.data[1].close == 2015.0

    @pytest.mark.asyncio
    async def test_get_price_data_error(self, price_service):
        """Test price data retrieval with error."""
        with patch.object(
            price_service._base_service,
            "get_price_data",
            side_effect=ValueError("Invalid commodity"),
        ):
            with pytest.raises(ValueError, match="Invalid commodity"):
                await price_service.get_price_data("INVALID")

    @pytest.mark.asyncio
    async def test_get_latest_price_success(
        self, price_service, mock_latest_price, mock_price_summary
    ):
        """Test successful latest price retrieval."""
        with (
            patch.object(
                price_service._base_service,
                "get_latest_price",
                return_value=mock_latest_price,
            ),
            patch.object(
                price_service._base_service,
                "get_price_summary",
                return_value=mock_price_summary,
            ),
        ):
            result = await price_service.get_latest_price("GOLD")

            assert isinstance(result, LatestPriceResponse)
            assert result.commodity == "GOLD"
            assert result.current_price == 2015.0
            assert result.change_24h == 0.5
            assert result.change_24h_abs == 10.075  # 2015.0 * 0.5 / 100
            assert result.change_24h_direction in ["up", "down", "neutral"]

    @pytest.mark.asyncio
    async def test_get_latest_price_error(self, price_service):
        """Test latest price retrieval with error."""
        with patch.object(
            price_service._base_service,
            "get_latest_price",
            side_effect=ValueError("API error"),
        ):
            with pytest.raises(ValueError, match="API error"):
                await price_service.get_latest_price("GOLD")
