"""Unit tests for MCP service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.mcp.service import MCPService
from app.mcp.models import (
    MCPContextRequest,
    MCPContextResponse,
    MCPInsightRequest,
    MCPInsightResponse,
)
from src.data.models.insight import AIInsight


@pytest.fixture
def mcp_service():
    """Create MCP service instance."""
    return MCPService()


@pytest.fixture
def mock_insight():
    """Mock AI insight."""
    return AIInsight(
        commodity="GOLD",
        summary="Test insight",
        key_factors=["Factor 1", "Factor 2"],
        price_outlook="Bullish",
        recommendation="Buy",
        sentiment="bullish",
        confidence=0.85,
        model="deepseek-chat",
    )


class TestMCPService:
    """Test cases for MCPService."""

    @pytest.mark.asyncio
    async def test_get_context_success(self, mcp_service):
        """Test successful context retrieval."""
        request = MCPContextRequest(
            query="gold price analysis",
            commodity="GOLD",
            max_tokens=1000,
            temperature=0.3,
        )

        result = await mcp_service.get_context(request)

        assert isinstance(result, MCPContextResponse)
        assert result.query == "gold price analysis"
        assert result.commodity == "GOLD"
        assert "Simulated MCP context" in result.context
        assert result.model == "gemini-pro"
        assert len(result.sources) > 0
        assert result.token_count > 0

    @pytest.mark.asyncio
    async def test_get_context_without_commodity(self, mcp_service):
        """Test context retrieval without commodity filter."""
        request = MCPContextRequest(
            query="market analysis", max_tokens=1000, temperature=0.3
        )

        result = await mcp_service.get_context(request)

        assert result.commodity is None
        assert "market analysis" in result.context

    @pytest.mark.asyncio
    async def test_get_insight_without_mcp(self, mcp_service, mock_insight):
        """Test insight generation without MCP enhancement."""
        request = MCPInsightRequest(
            commodity="GOLD",
            price_data={"current_price": 2000.0, "change_24h": 0.5},
            news_summary="Market is stable",
            use_mcp=False,
        )

        with patch.object(
            mcp_service._base_service, "generate_insight", return_value=mock_insight
        ):
            result = await mcp_service.get_insight(request)

            assert isinstance(result, MCPInsightResponse)
            assert result.commodity == "GOLD"
            assert result.insight == mock_insight
            assert result.mcp_context is None
            assert result.use_mcp is False

    @pytest.mark.asyncio
    async def test_get_insight_with_mcp(self, mcp_service, mock_insight):
        """Test insight generation with MCP enhancement."""
        request = MCPInsightRequest(
            commodity="GOLD",
            price_data={"current_price": 2000.0, "change_24h": 0.5},
            news_summary="Market is stable",
            use_mcp=True,
            mcp_query="gold price analysis",
        )

        with patch.object(
            mcp_service._base_service, "generate_insight", return_value=mock_insight
        ):
            result = await mcp_service.get_insight(request)

            assert isinstance(result, MCPInsightResponse)
            assert result.commodity == "GOLD"
            assert result.insight == mock_insight
            assert result.mcp_context is not None
            assert result.mcp_context.query == "gold price analysis"
            assert result.mcp_context.commodity == "GOLD"
            assert result.use_mcp is True

    @pytest.mark.asyncio
    async def test_get_insight_error(self, mcp_service):
        """Test insight generation with error."""
        request = MCPInsightRequest(
            commodity="INVALID",
            price_data={"current_price": 2000.0, "change_24h": 0.5},
            news_summary="Market is stable",
            use_mcp=False,
        )

        with patch.object(
            mcp_service._base_service,
            "generate_insight",
            side_effect=ValueError("Invalid commodity"),
        ):
            with pytest.raises(ValueError, match="Invalid commodity"):
                await mcp_service.get_insight(request)
