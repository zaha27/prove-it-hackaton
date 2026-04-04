"""Tests for data models."""

from datetime import datetime

from src.data.models.commodity import COMMODITIES, GOLD, OIL, CommodityCategory
from src.data.models.insight import AIInsight
from src.data.models.news import NewsArticle
from src.data.models.price import PriceData


class TestCommodity:
    """Test cases for commodity models."""

    def test_gold_commodity(self):
        """Test GOLD commodity definition."""
        assert GOLD.symbol == "GOLD"
        assert GOLD.name == "Gold"
        assert GOLD.category == CommodityCategory.METALS
        assert GOLD.yfinance_symbol == "GC=F"

    def test_oil_commodity(self):
        """Test OIL commodity definition."""
        assert OIL.symbol == "OIL"
        assert OIL.name == "Crude Oil (WTI)"
        assert OIL.category == CommodityCategory.ENERGY
        assert OIL.yfinance_symbol == "CL=F"

    def test_commodities_dict(self):
        """Test commodities dictionary."""
        assert "GOLD" in COMMODITIES
        assert "OIL" in COMMODITIES
        assert COMMODITIES["GOLD"] == GOLD
        assert COMMODITIES["OIL"] == OIL


class TestPriceData:
    """Test cases for price data model."""

    def test_price_data_creation(self):
        """Test creating price data."""
        data = PriceData(
            commodity="GOLD",
            dates=["2024-01-01", "2024-01-02"],
            open=[2000.0, 2010.0],
            high=[2010.0, 2020.0],
            low=[1990.0, 2000.0],
            close=[2005.0, 2015.0],
            volume=[100000, 120000],
        )
        assert data.commodity == "GOLD"
        assert len(data.dates) == 2

    def test_latest_price(self):
        """Test getting latest price."""
        data = PriceData(
            commodity="GOLD",
            dates=["2024-01-01", "2024-01-02"],
            open=[2000.0, 2010.0],
            high=[2010.0, 2020.0],
            low=[1990.0, 2000.0],
            close=[2005.0, 2015.0],
            volume=[100000, 120000],
        )
        assert data.latest_price() == 2015.0

    def test_price_change_24h(self):
        """Test calculating 24h price change."""
        data = PriceData(
            commodity="GOLD",
            dates=["2024-01-01", "2024-01-02"],
            open=[2000.0, 2010.0],
            high=[2010.0, 2020.0],
            low=[1990.0, 2000.0],
            close=[2000.0, 2100.0],
            volume=[100000, 120000],
        )
        change, pct_change = data.price_change_24h()
        assert change == 100.0
        assert pct_change == 5.0


class TestNewsArticle:
    """Test cases for news article model."""

    def test_news_article_creation(self):
        """Test creating news article."""
        article = NewsArticle(
            id="test_001",
            title="Test Article",
            source="Test Source",
            date="2024-01-15",
            content="Test content",
            sentiment="positive",
            sentiment_score=0.75,
            commodity="GOLD",
        )
        assert article.id == "test_001"
        assert article.title == "Test Article"
        assert article.sentiment == "positive"

    def test_to_qdrant_payload(self):
        """Test converting to Qdrant payload."""
        article = NewsArticle(
            id="test_001",
            title="Test Article",
            source="Test Source",
            date="2024-01-15",
            content="Test content",
            sentiment="positive",
            sentiment_score=0.75,
            commodity="GOLD",
        )
        payload = article.to_qdrant_payload()
        assert payload["id"] == "test_001"
        assert payload["title"] == "Test Article"
        assert payload["sentiment"] == "positive"


class TestAIInsight:
    """Test cases for AI insight model."""

    def test_insight_creation(self):
        """Test creating AI insight."""
        insight = AIInsight(
            commodity="GOLD",
            summary="Bullish trend detected",
            key_factors=["Factor 1", "Factor 2"],
            price_outlook="Resistance at $2050",
            recommendation="Buy on dips",
            sentiment="bullish",
            confidence=0.85,
        )
        assert insight.commodity == "GOLD"
        assert insight.sentiment == "bullish"
        assert insight.confidence == 0.85

    def test_to_markdown(self):
        """Test converting to markdown."""
        insight = AIInsight(
            commodity="GOLD",
            summary="Bullish trend detected",
            key_factors=["Factor 1", "Factor 2"],
            price_outlook="Resistance at $2050",
            recommendation="Buy on dips",
            sentiment="bullish",
            confidence=0.85,
        )
        markdown = insight.to_markdown()
        assert "GOLD" in markdown
        assert "BULLISH" in markdown
        assert "85%" in markdown
        assert "Factor 1" in markdown
