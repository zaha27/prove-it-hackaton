"""Unit tests for change service."""

import pytest
from unittest.mock import patch
from datetime import datetime

from app.change.service import ChangeService
from app.change.models import Change24hResponse, ChangeComparisonResponse


@pytest.fixture
def change_service():
    """Create change service instance."""
    return ChangeService()


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


class TestChangeService:
    """Test cases for ChangeService."""

    @pytest.mark.asyncio
    async def test_get_24h_change_success(self, change_service, mock_latest_price):
        """Test successful 24h change retrieval."""
        with patch.object(
            change_service._base_service,
            "get_latest_price",
            return_value=mock_latest_price,
        ):
            result = await change_service.get_24h_change("GOLD")

            assert isinstance(result, Change24hResponse)
            assert result.commodity == "GOLD"
            assert result.current_price == 2015.0
            assert result.change_24h == 0.5
            assert result.change_24h_abs == 10.075  # 2015.0 * 0.5 / 100
            assert result.change_24h_direction == "up"  # Since 0.5 > 0.1

    @pytest.mark.asyncio
    async def test_get_24h_change_down(self, change_service):
        """Test 24h change with negative value."""
        mock_data = {
            "current_price": 1985.0,
            "change_24h": -0.8,
        }
        with patch.object(
            change_service._base_service, "get_latest_price", return_value=mock_data
        ):
            result = await change_service.get_24h_change("GOLD")

            assert result.change_24h == -0.8
            assert result.change_24h_direction == "down"  # Since -0.8 < -0.1

    @pytest.mark.asyncio
    async def test_get_24h_change_neutral(self, change_service):
        """Test 24h change with neutral value."""
        mock_data = {
            "current_price": 2000.0,
            "change_24h": 0.05,
        }
        with patch.object(
            change_service._base_service, "get_latest_price", return_value=mock_data
        ):
            result = await change_service.get_24h_change("GOLD")

            assert result.change_24h == 0.05
            assert result.change_24h_direction == "neutral"  # Since -0.1 <= 0.05 <= 0.1

    @pytest.mark.asyncio
    async def test_get_24h_change_error(self, change_service):
        """Test 24h change retrieval with error."""
        with patch.object(
            change_service._base_service,
            "get_latest_price",
            side_effect=ValueError("Invalid commodity"),
        ):
            with pytest.raises(ValueError, match="Invalid commodity"):
                await change_service.get_24h_change("INVALID")

    @pytest.mark.asyncio
    async def test_compare_24h_change_success(self, change_service):
        """Test successful 24h change comparison."""
        base_data = {
            "current_price": 2000.0,
            "change_24h": 0.5,
        }
        target_data = {
            "current_price": 25.0,
            "change_24h": 1.2,
        }

        with patch.object(
            change_service._base_service,
            "get_latest_price",
            side_effect=[base_data, target_data],
        ):
            result = await change_service.compare_24h_change("GOLD", "SILVER")

            assert isinstance(result, ChangeComparisonResponse)
            assert result.base_commodity == "GOLD"
            assert result.target_commodity == "SILVER"
            assert result.base_change_24h == 0.5
            assert result.target_change_24h == 1.2
            assert result.change_difference == 0.7  # 1.2 - 0.5

    @pytest.mark.asyncio
    async def test_compare_24h_change_error(self, change_service):
        """Test 24h change comparison with error."""
        with patch.object(
            change_service._base_service,
            "get_latest_price",
            side_effect=ValueError("API error"),
        ):
            with pytest.raises(ValueError, match="API error"):
                await change_service.compare_24h_change("GOLD", "SILVER")
