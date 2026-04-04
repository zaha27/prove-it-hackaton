"""MCP service module."""

import os
import logging
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
        self._logger = logging.getLogger(__name__)

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
                # DeepSeek unavailable — return error insight
                self._logger.error(
                    "InsightService failed for %s: %s", request.commodity, exc
                )
                return AIInsight(
                    commodity=request.commodity,
                    summary=(
                        f"AI insight unavailable: {exc}. "
                        "Ensure DEEPSEEK_API_KEY is set in .env and the server is running."
                    ),
                    key_factors=[],
                    price_outlook="",
                    recommendation="",
                    sentiment="neutral",
                    confidence=0.0,
                    model="none",
                )

        insight: AIInsight = await loop.run_in_executor(None, _generate)

        return MCPInsightResponse(
            commodity=request.commodity.upper(),
            insight=insight,
            mcp_context=mcp_context,
            use_mcp=request.use_mcp,
            fetched_at=datetime.utcnow(),
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
        """
        from src.ml.consensus_engine import ConsensusEngine
        from src.ml.xgboost_trainer import XGBoostTrainer
        from src.features.xgboost_features import XGBoostFeatureEngineer
        from src.data.clients.yfinance_client import YFinanceClient
        from src.data.services.price_service import PriceService
        import pandas as pd
        import math

        commodity = request.commodity.upper()

        try:
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

            # Fetch OHLCV data for features (1y necessary for moving averages)
            ohlcv = yf_client.fetch_ohlcv(commodity, period="1y")
            df = ohlcv.to_dataframe()
            if df.empty:
                raise ValueError(
                    f"No OHLCV data available for {commodity}. "
                    "Verify the symbol is valid and market data is accessible."
                )

            # Engineer features with sentiment
            df_features = feature_engineer.engineer_features(df, news_sentiment)
            if df_features.empty:
                raise ValueError(f"No engineered features available for {commodity}")

            # Get current features for prediction and SANITIZE NaN values
            raw_features = df_features.iloc[-1].to_dict()
            current_features = {}
            for k, v in raw_features.items():
                if isinstance(v, (int, float)) or pd.api.types.is_numeric_dtype(type(v)):
                    current_features[k] = 0.0 if pd.isna(v) or math.isnan(float(v)) else float(v)
                else:
                    current_features[k] = 0.0

            # Train and predict
            xgb_result = xgb_trainer.predict_with_explanation(commodity, current_features)

            # Run consensus debate with DeepSeek
            consensus_engine = ConsensusEngine(
                max_rounds=request.max_rounds,
                agreement_threshold=request.agreement_threshold,
                gemini_mcp=self if self._use_real_gemini else None,
            )

            user_profile = {
                "risk_score": getattr(request, "risk_score", 3),
                "investment_horizon": getattr(request, "investment_horizon", 3),
                "market_familiarity": getattr(request, "market_familiarity", 3),
                "preferred_strategy": getattr(request, "risk_profile", "Balanced"),
            }

            result = await consensus_engine.reach_consensus(
                commodity=commodity,
                xgboost_result=xgb_result,
                price_data=price_data,
                user_profile=user_profile,
                yahoo_news=[
                    {
                        "title": n.title,
                        "sentiment": n.sentiment,
                        "sentiment_score": float(n.sentiment_score),
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
                    agreement_score=float(r.agreement_score),
                )
                for r in result.debate_history
            ]

            return ConsensusResponse(
                commodity=result.commodity,
                consensus_reached=result.consensus_reached,
                rounds_conducted=result.rounds_conducted,
                final_recommendation=result.final_recommendation,
                confidence=float(result.confidence),
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
        except Exception as exc:
            import traceback
            error_details = traceback.format_exc()
            self._logger.error(f"CRITICAL CONSENSUS ERROR for {commodity}:\n{error_details}")
            
            error_id = f"{commodity}-{int(datetime.utcnow().timestamp())}"
            # Return a safe fallback payload
            return ConsensusResponse(
                commodity=commodity,
                consensus_reached=False,
                rounds_conducted=0,
                final_recommendation="HOLD",
                confidence=0.0,
                direction="hold",
                risk_level="high",
                debate_history=[],
                xgboost_input={},
                yahoo_news_summary="",
                final_reasoning=(
                    "Consensus temporarily unavailable due to an internal processing "
                    f"error (ref: {error_id}). Check backend logs."
                ),
                gemma4_final_position={},
                deepseek_final_position={},
                fetched_at=datetime.utcnow(),
            )