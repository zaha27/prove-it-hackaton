"""Unit tests for price router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.price.models import PriceDataResponse, LatestPriceResponse, PricePoint
from datetime import datetime


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_price_data_response():
    """Mock price data response."""
    return PriceDataResponse(
        commodity="GOLD",
        data=[
            PricePoint(
                timestamp=datetime(2024, 1, 1),
                open=2000.0,
                high=2010.0,
                low=1990.0,
                close=2005.0,
                volume=100000,
            )
        ],
        fetched_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_latest_price_response():
    """Mock latest price response."""
    return LatestPriceResponse(
        commodity="GOLD",
        current_price=2015.0,
        change_24h=0.5,
        change_24h_abs=10.075,
        high_24h=2020.0,
        low_24h=2000.0,
        fetched_at=datetime.utcnow(),
    )


class TestPriceRouter:
    """Test cases for price router."""

    def test_get_price_data_success(self, client, mock_price_data_response):
        """Test successful price data retrieval."""
        with patch("app.price.service.PriceService.get_price_data") as mock_get_price:
            mock_get_price.return_value = mock_price_data_response

            response = client.get("/api/v1/price/data/GOLD")

            assert response.status_code == 200
            data = response.json()
            assert data["commodity"] == "GOLD"
            assert len(data["data"]) == 1
            assert data["data"][0]["close"] == 2005.0

    def test_get_price_data_invalid_commodity(self, client):
        """Test price data retrieval with invalid commodity."""
        with patch("app.price.service.PriceService.get_price_data") as mock_get_price:
            mock_get_price.side_effect = ValueError("Unsupported commodity: INVALID")

            response = client.get("/api/v1/price/data/INVALID")

            assert response.status_code == 400
            assert "Unsupported commodity" in response.json()["detail"]

    def test_get_latest_price_success(self, client, mock_latest_price_response):
        """Test successful latest price retrieval."""
        with patch("app.price.service.PriceService.get_latest_price") as mock_get_price:
            mock_get_price.return_value = mock_latest_price_response

            response = client.get("/api/v1/price/latest/GOLD")

            assert response.status_code == 200
            data = response.json()
            assert data["commodity"] == "GOLD"
            assert data["current_price"] == 2015.0
            assert data["change_24h"] == 0.5

    def test_get_latest_price_error(self, client):
        """Test latest price retrieval with error."""
        with patch("app.price.service.PriceService.get_latest_price") as mock_get_price:
            mock_get_price.side_effect = ValueError("API error")

            response = client.get("/api/v1/price/latest/GOLD")

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]

    def test_get_supported_commodities(self, client):
        """Test getting supported commodities."""
        with patch("app.price.router.config") as mock_config:
            mock_config.commodity_symbols = {"GOLD": "GC=F", "SILVER": "SI=F"}

            response = client.get("/api/v1/price/symbols")

            assert response.status_code == 200
            data = response.json()
            assert "symbols" in data
            assert set(data["symbols"]) == {"GOLD", "SILVER"}
