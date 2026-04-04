"""Tests for the data API module."""

import pytest

from src.data.api.data_api import (
    get_supported_commodities,
    is_commodity_supported,
)


class TestDataAPI:
    """Test cases for the public data API."""

    def test_get_supported_commodities(self):
        """Test getting supported commodities."""
        commodities = get_supported_commodities()
        assert "GOLD" in commodities
        assert "OIL" in commodities
        assert len(commodities) == 2

    def test_is_commodity_supported(self):
        """Test commodity support check."""
        assert is_commodity_supported("GOLD") is True
        assert is_commodity_supported("OIL") is True
        assert is_commodity_supported("gold") is True  # Case insensitive
        assert is_commodity_supported("SILVER") is False
        assert is_commodity_supported("INVALID") is False
