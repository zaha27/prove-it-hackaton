"""Unit tests for macro router."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMacroRouter:
    """Test cases for macro router."""

    def test_get_macro_news_success(self, client):
        """Test successful macro news retrieval."""
        mock_news = [
            {
                "title": "Iran energy exports under pressure",
                "source": "reuters.com",
                "timestamp": "2026-04-04T08:00:00Z",
                "sentiment": "neutral",
                "summary": "",
                "url": "https://www.reuters.com/world/middle-east/example",
                "country_iso3": "IRN",
            },
            {
                "title": "China demand outlook supports metals",
                "source": "reuters.com",
                "timestamp": "2026-04-04T09:00:00Z",
                "sentiment": "neutral",
                "summary": "",
                "url": "https://www.reuters.com/world/china/example",
                "country_iso3": "CHN",
            },
        ]
        with patch(
            "src.data.services.news_service.fetch_real_world_news",
            return_value=mock_news,
        ):
            response = client.get("/macro/news")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
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
