"""Unit tests for macro router."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMacroRouter:
    """Test cases for macro router."""

    def test_get_macro_news_success(self, client):
        """Test successful macro news retrieval."""
        response = client.get("/macro/news")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        for item in data:
            assert set(item.keys()) == {
                "title",
                "source",
                "timestamp",
                "sentiment",
                "summary",
            }

    def test_get_macro_insight_success(self, client):
        """Test successful macro insight retrieval."""
        response = client.get("/macro/insight")

        assert response.status_code == 200
        data = response.json()
        assert "insight" in data
        assert isinstance(data["insight"], str)
        assert "AI Insight — World Macro View" in data["insight"]
        assert "Russia-Ukraine war" in data["insight"]
        assert "Strait of Hormuz" in data["insight"]
        assert "Red Sea" in data["insight"]
        assert "Fed policy" in data["insight"]
        assert "China demand" in data["insight"]
