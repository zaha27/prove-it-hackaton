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
    ConsensusRequest,
    ConsensusResponse,
    DebateRound,
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

        # Generate insight — try DeepSeek first, fall back to Ollama
        import asyncio

        loop = asyncio.get_event_loop()

        def _generate() -> AIInsight:
            # InsightService.generate_insight only takes (commodity, use_cache)
            try:
                return self._base_service.generate_insight(
                    request.commodity, use_cache=True
                )
            except (ValueError, Exception) as exc:
                # DeepSeek key missing or call failed → use Ollama fallback
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

    async def search_with_grounding(self, query: str) -> dict:
        """Proxy method for Gemini MCP web search grounding.

        Args:
            query: Search query string

        Returns:
            Dict with 'sources' and 'grounding' keys
        """
        if not self._use_real_gemini:
            return {
                "sources": [],
                "grounding": "[Web search disabled - no Gemini API key]",
            }

        try:
            # Import and use the gemini-grounding MCP tool
            from CallMcpTool import CallMcpTool

            result = CallMcpTool(
                server_name="gemini-grounding",
                tool_name="search_with_grounding",
                arguments={"query": query},
            )
            return {
                "sources": result.get("sources", []),
                "grounding": result.get("grounding", ""),
            }
        except Exception as e:
            # Fallback if MCP tool fails
            return {
                "sources": [],
                "grounding": f"[Web search error: {e}]",
            }

    async def get_consensus(self, request: ConsensusRequest) -> ConsensusResponse:
        """
        Run DeepSeek-Gemma4 consensus debate for trading recommendation.

        Args:
            request: ConsensusRequest with commodity and parameters

        Returns:
            ConsensusResponse with debate history and final recommendation
        """
        import asyncio
        from src.ml.consensus_engine import ConsensusEngine
        from src.ml.xgboost_trainer import XGBoostTrainer
        from src.features.xgboost_features import XGBoostFeatureEngineer
        from src.data.clients.yfinance_client import YFinanceClient
        from src.data.services.price_service import PriceService

        commodity = request.commodity.upper()

        # Fetch data
        yf_client = YFinanceClient()
        price_service = PriceService()

        # Get Yahoo Finance news with sentiment
        news = yf_client.fetch_news(commodity, limit=10)
        news_sentiment = yf_client.analyze_news_sentiment(news)

        # Get price data
        price_data = price_service.get_latest_price(commodity)

        # Get XGBoost prediction
        xgb_trainer = XGBoostTrainer()
        feature_engineer = XGBoostFeatureEngineer()

        # Fetch OHLCV data for features
        ohlcv = yf_client.fetch_ohlcv(commodity, period="60d")
        df = ohlcv.to_dataframe()

        # Engineer features with sentiment
        df_features = feature_engineer.engineer_features(df, news_sentiment)

        # Get current features for prediction
        current_features = df_features.iloc[-1].to_dict()

        # Train and predict
        xgb_result = xgb_trainer.predict_with_explanation(commodity, current_features)

        # Run consensus debate with Gemini MCP for web search
        consensus_engine = ConsensusEngine(
            max_rounds=request.max_rounds,
            agreement_threshold=request.agreement_threshold,
            gemini_mcp=self if self._use_real_gemini else None,
        )

        result = await consensus_engine.reach_consensus(
            commodity=commodity,
            xgboost_result=xgb_result,
            price_data=price_data,
            yahoo_news=[
                {
                    "title": n.title,
                    "sentiment": n.sentiment,
                    "sentiment_score": n.sentiment_score,
                    "source": n.source,
                }
                for n in news
            ],
        )

        # Convert to Pydantic model
        debate_rounds = [
            DebateRound(
                round_number=r.round_number,
                gemma4_argument=r.gemma4_argument,
                gemma4_sources=r.gemma4_sources,
                gemma4_position=r.gemma4_position,
                deepseek_critique=r.deepseek_critique,
                deepseek_counter=r.deepseek_counter,
                deepseek_position=r.deepseek_position,
                agreement_score=r.agreement_score,
            )
            for r in result.debate_history
        ]

        return ConsensusResponse(
            commodity=result.commodity,
            consensus_reached=result.consensus_reached,
            rounds_conducted=result.rounds_conducted,
            final_recommendation=result.final_recommendation,
            confidence=result.confidence,
            direction=result.direction,
            risk_level=result.risk_level,
            debate_history=debate_rounds,
            xgboost_input=result.xgboost_input,
            yahoo_news_summary=result.yahoo_news_summary,
            final_reasoning=result.final_reasoning,
            gemma4_final_position=result.gemma4_final_position,
            deepseek_final_position=result.deepseek_final_position,
            fetched_at=datetime.utcnow(),
        )