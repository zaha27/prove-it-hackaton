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
        assert 5 <= len(data) <= 10
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
        assert "Macro Context (Dobânzi/Bănci Centrale)" in data["insight"]
        assert "Geopolitică & Supply Chain" in data["insight"]
        assert "Concluzie / Risc Global" in data["insight"]

