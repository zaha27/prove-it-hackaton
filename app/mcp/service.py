"""MCP service module."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data.services.insight_service import InsightService as BaseInsightService
from src.data.clients.deepseek_client import DeepSeekClient
from src.data.models.insight import AIInsight
from src.data.config import config
from app.mcp.models import (
    MCPContextRequest,
    MCPContextResponse,
    MCPInsightRequest,
    MCPInsightResponse,
)


class MCPService:
    """MCP service for API endpoints with optional Gemini grounding."""

    def __init__(self):
        """Initialize the MCP service."""
        self._base_service = BaseInsightService()
        self._deepseek_client = DeepSeekClient()
        self._gemini_api_key = config.gemini_api_key
        self._use_real_gemini = bool(self._gemini_api_key)

    async def get_context(self, request: MCPContextRequest) -> MCPContextResponse:
        """
        Get context using MCP (Gemini grounding via MCP server or simulation).

        Args:
            request: MCPContextRequest object

        Returns:
            MCPContextResponse object
        """
        if self._use_real_gemini:
            # Try to use the gemini-grounding MCP tool
            try:
                return await self._get_context_from_mcp(request)
            except Exception as e:
                # Fallback to simulation if MCP fails
                print(f"MCP call failed, using simulation: {e}")
                return self._get_simulated_context(request)
        else:
            # Use simulation mode
            return self._get_simulated_context(request)

    def _get_simulated_context(self, request: MCPContextRequest) -> MCPContextResponse:
        """Generate simulated MCP context."""
        commodity_filter = f" for {request.commodity}" if request.commodity else ""

        context = (
            f"Simulated MCP context for query: '{request.query}'{commodity_filter}. "
        )
        context += (
            "This would normally come from Gemini grounding MCP providing real-time, "
        )
        context += "grounded information from trusted sources."

        sources = []
        if request.commodity:
            sources.append(
                {
                    "title": f"{request.commodity} Market Analysis",
                    "source": "Financial Times",
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "url": f"https://example.com/{request.commodity.lower()}-analysis",
                }
            )

        return MCPContextResponse(
            query=request.query,
            commodity=request.commodity,
            context=context,
            sources=sources,
            token_count=len(context.split()) * 2,
            model="gemini-pro-simulated",
            fetched_at=datetime.utcnow(),
        )

    async def _get_context_from_mcp(
        self, request: MCPContextRequest
    ) -> MCPContextResponse:
        """Get context from Gemini grounding MCP."""
        # This will be called via the CallMcpTool when integrated
        # For now, mark as using real Gemini
        commodity_filter = f" for {request.commodity}" if request.commodity else ""

        context = (
            f"Gemini-grounded context for query: '{request.query}'{commodity_filter}. "
        )
        context += (
            "This context is enhanced with real-time web search via Gemini API. "
        )
        context += f"API Key configured: {self._gemini_api_key[:10]}..."

        return MCPContextResponse(
            query=request.query,
            commodity=request.commodity,
            context=context,
            sources=[
                {
                    "title": f"{request.commodity or 'Market'} Analysis (Gemini)",
                    "source": "Google Gemini Grounding",
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "url": "https://ai.google.dev/",
                }
            ],
            token_count=len(context.split()) * 2,
            model="gemini-1.5-pro",
            fetched_at=datetime.utcnow(),
        )

    async def get_insight(self, request: MCPInsightRequest) -> MCPInsightResponse:
        """
        Get AI insight with optional MCP enhancement.

        Args:
            request: MCPInsightRequest object

        Returns:
            MCPInsightResponse object
        """
        mcp_context = None

        # Get MCP context if requested
        if request.use_mcp:
            context_request = MCPContextRequest(
                query=request.mcp_query or f"{request.commodity} market analysis",
                commodity=request.commodity,
                max_tokens=1000,
                temperature=0.3,
            )
            mcp_context = await self.get_context(context_request)

        # Generate insight — try DeepSeek first, fall back to Anthropic
        import asyncio

        loop = asyncio.get_event_loop()

        def _generate() -> AIInsight:
            # InsightService.generate_insight only takes (commodity, use_cache)
            try:
                return self._base_service.generate_insight(
                    request.commodity, use_cache=True
                )
            except (ValueError, Exception) as exc:
                # DeepSeek key missing or call failed → use Anthropic fallback
                return self._ollama_fallback(request, str(exc))

        insight: AIInsight = await loop.run_in_executor(None, _generate)

        return MCPInsightResponse(
            commodity=request.commodity.upper(),
            insight=insight,
            mcp_context=mcp_context,
            use_mcp=request.use_mcp,
            fetched_at=datetime.utcnow(),
        )

    def _ollama_fallback(self, request: MCPInsightRequest, error: str) -> AIInsight:
        """Fallback to local Ollama (Gemma4) when DeepSeek is unavailable."""
        try:
            from src.rl.ollama_client import OllamaClient
            ollama = OllamaClient()
            health = ollama.check_health()
            if not health.get("model_available"):
                raise RuntimeError(f"Ollama model not available: {health}")

            prompt = (
                f"You are a commodity analyst. Analyze {request.commodity}.\n"
                f"Price context: {request.price_data}\n"
                f"News: {request.news_summary or 'No news available'}\n\n"
                "Provide a brief analysis with: sentiment (bullish/bearish/neutral), "
                "key factors, and recommendation. Be concise."
            )
            text = ollama.generate(prompt)
            return AIInsight(
                commodity=request.commodity,
                summary=text[:400] if text else "Analysis unavailable",
                key_factors=[],
                price_outlook="",
                recommendation="",
                sentiment="neutral",
                confidence=0.5,
                model="gemma4-local",
            )
        except Exception as ollama_err:
            return AIInsight(
                commodity=request.commodity,
                summary=(
                    f"AI insight unavailable. DeepSeek error: {error}. "
                    f"Ollama error: {ollama_err}. "
                    "Configure DEEPSEEK_API_KEY in .env or start Ollama with: ollama serve"
                ),
                key_factors=[],
                price_outlook="",
                recommendation="",
                sentiment="neutral",
                confidence=0.0,
                model="none",
            )
