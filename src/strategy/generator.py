"""Strategy generator with multi-variant generation and Chain-of-Thought reasoning."""

import json
from dataclasses import dataclass
from typing import Any

from src.backtest.engine import BacktestEngine
from src.data.clients.deepseek_client import DeepSeekClient
from src.data.config import config
from src.data.ingestion.prediction_tracker import PredictionTracker
from src.data.models.insight import AIInsight
from src.data.services.news_service import NewsService
from src.data.services.price_service import PriceService
from src.features.xgboost_features import XGBoostFeatureEngineer
from src.ml.prediction_service import PredictionService
from src.rl.deep_researcher import DeepResearcher


@dataclass
class StrategyVariant:
    """Strategy variant definition."""

    variant: str  # conservative, balanced, aggressive
    recommendation: str  # BUY, SELL, HOLD
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: str
    reasoning: str
    key_factors: list[str]
    risk_level: str


class StrategyGenerator:
    """Generates multi-variant trading strategies with CoT reasoning."""

    def __init__(self) -> None:
        """Initialize the strategy generator."""
        self.llm_client = DeepSeekClient()
        self.price_service = PriceService()
        self.news_service = NewsService()
        self.backtest_engine = BacktestEngine()
        self.prediction_tracker = PredictionTracker()
        self.deep_researcher = DeepResearcher()
        self.prediction_service = PredictionService()
        self.feature_engineer = XGBoostFeatureEngineer()
        self.low_confidence_threshold = 0.5

    def generate_strategies(
        self,
        commodity: str,
        use_rl: bool = True,
    ) -> dict[str, Any]:
        """Generate validated strategies for a commodity.

        Args:
            commodity: Commodity symbol
            use_rl: Whether to use RL-weighted RAG

        Returns:
            Dictionary with strategies and validation results
        """
        # Gather market data
        price_data = self.price_service.get_price_data(commodity, period="1mo")
        price_summary = self.price_service.get_price_summary(commodity)
        latest_price = price_data.close[-1] if price_data.close else 0

        # Get news summary
        news_summary = self.news_service.get_news_summary(commodity, max_articles=5)

        # Get RL-weighted successful patterns if enabled
        rl_context = ""
        if use_rl:
            similar_success = self.prediction_tracker.find_similar_successful_predictions(
                news_summary, commodity, top_k=3
            )
            if similar_success:
                rl_context = "\n\nHistorically Successful Similar Strategies:\n"
                for i, pattern in enumerate(similar_success, 1):
                    rl_context += f"{i}. Return: {pattern['actual_return']:+.1f}%\n"
                    rl_context += f"   Reasoning: {pattern['reasoning'][:200]}...\n"

        # Generate multi-variant strategies via LLM
        strategies = self._generate_llm_strategies(
            commodity=commodity,
            current_price=latest_price,
            price_summary=price_summary,
            news_summary=news_summary,
            rl_context=rl_context,
        )

        # Backtest each strategy
        validated_strategies = []
        for strategy in strategies:
            # Prepare strategy for backtesting
            backtest_strategy = {
                "id": f"strat_{commodity}_{strategy.variant}",
                "variant": strategy.variant,
                "recommendation": strategy.recommendation,
                "target_pct": abs(strategy.target_price / strategy.entry_price - 1),
                "stop_pct": abs(strategy.stop_loss / strategy.entry_price - 1),
            }

            # Run backtest
            backtest_result = self.backtest_engine.backtest_strategy(
                commodity=commodity,
                current_prices=price_data.close[-20:],  # Last 20 days
                current_volumes=price_data.volume[-20:],
                strategy=backtest_strategy,
            )

            # Calculate confidence score
            confidence = self.backtest_engine.get_confidence_score(backtest_result)

            # Track prediction for RL
            if backtest_result.get("valid", False):
                prediction_id = self.prediction_tracker.track_prediction(
                    commodity=commodity,
                    recommendation=strategy.recommendation,
                    entry_price=strategy.entry_price,
                    target_price=strategy.target_price,
                    stop_loss=strategy.stop_loss,
                    reasoning=strategy.reasoning,
                    strategy_variant=strategy.variant,
                    metadata={
                        "confidence_score": confidence,
                        "win_rate": backtest_result.get("metrics", {}).get("win_rate", 0),
                        "sharpe": backtest_result.get("metrics", {}).get("sharpe_ratio", 0),
                    },
                )
            else:
                prediction_id = None

            validated_strategies.append({
                "strategy": strategy,
                "backtest": backtest_result,
                "confidence_score": confidence,
                "prediction_id": prediction_id,
                "status": backtest_result.get("status", "rejected"),
            })

        # Rank strategies by confidence
        validated_strategies.sort(
            key=lambda x: x["confidence_score"],
            reverse=True,
        )

        # Check for low confidence - trigger Gemma4 deep reasoning
        best_confidence = validated_strategies[0]["confidence_score"] if validated_strategies else 0
        gemma4_analysis = None

        if best_confidence < self.low_confidence_threshold:
            print(f"⚠️ Low confidence detected ({best_confidence:.2f}), triggering Gemma4 deep reasoning...")
            gemma4_analysis = self._trigger_gemma4_analysis(
                commodity, validated_strategies, price_data, news_summary
            )

        # Get best validated strategy
        best_strategy = next(
            (s for s in validated_strategies if s["status"] == "validated"),
            None,
        )

        # Get XGBoost + Gemma4 prediction
        print(f"🔮 Getting XGBoost prediction for {commodity}...")
        try:
            xgboost_prediction = self.prediction_service.predict(
                commodity, target_horizon=7
            )
        except Exception as e:
            print(f"   Warning: XGBoost prediction failed: {e}")
            xgboost_prediction = None

        return {
            "commodity": commodity,
            "current_price": latest_price,
            "current_context": {
                "trend": price_summary.get("trend", "neutral"),
                "volatility": self._assess_volatility(price_data),
                "news_sentiment": self._get_avg_sentiment(commodity),
            },
            "strategies": validated_strategies,
            "best_strategy": best_strategy,
            "gemma4_analysis": gemma4_analysis,
            "xgboost_prediction": xgboost_prediction,
            "generated_at": json.dumps({}),  # Will be set by caller
        }

    def _generate_llm_strategies(
        self,
        commodity: str,
        current_price: float,
        price_summary: dict[str, Any],
        news_summary: str,
        rl_context: str,
    ) -> list[StrategyVariant]:
        """Generate strategies via LLM with Chain-of-Thought reasoning.

        Args:
            commodity: Commodity symbol
            current_price: Current price
            price_summary: Price summary data
            news_summary: News summary
            rl_context: RL context from past successful strategies

        Returns:
            List of strategy variants
        """
        prompt = self._build_strategy_prompt(
            commodity, current_price, price_summary, news_summary, rl_context
        )

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert quantitative trading strategist. Generate precise trading strategies with specific price levels."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            response_text = response.choices[0].message.content or ""
            return self._parse_strategy_response(response_text, current_price)

        except Exception as e:
            print(f"Error generating strategies: {e}")
            # Return default strategies
            return self._generate_default_strategies(commodity, current_price)

    def _build_strategy_prompt(
        self,
        commodity: str,
        current_price: float,
        price_summary: dict[str, Any],
        news_summary: str,
        rl_context: str,
    ) -> str:
        """Build the strategy generation prompt.

        Args:
            commodity: Commodity symbol
            current_price: Current price
            price_summary: Price summary
            news_summary: News summary
            rl_context: RL context

        Returns:
            Formatted prompt
        """
        return f"""Generate 3 trading strategy variants for {commodity} using Chain-of-Thought reasoning.

## Current Market Data
- Current Price: ${current_price:,.2f}
- 30-Day High: ${price_summary.get('high_30d', 0):,.2f}
- 30-Day Low: ${price_summary.get('low_30d', 0):,.2f}
- 7-Day Change: {price_summary.get('change_7d_pct', 0):+.2f}%
- 30-Day Change: {price_summary.get('change_30d_pct', 0):+.2f}%

## Recent News Context
{news_summary}
{rl_context}

## Task
Generate 3 strategy variants with specific price targets:

### 1. CONSERVATIVE Strategy
- Tight stop-loss (1-2%)
- Modest profit target (2-4%)
- Focus on high win rate
- Smaller position size

### 2. BALANCED Strategy
- Moderate stop-loss (2-3%)
- Moderate profit target (4-7%)
- Balanced risk/reward
- Standard position size

### 3. AGGRESSIVE Strategy
- Wider stop-loss (3-5%)
- Ambitious profit target (7-12%)
- Higher risk tolerance
- Larger position size (if conviction high)

## Output Format
Return ONLY a valid JSON object:
{{
    "conservative": {{
        "recommendation": "BUY|SELL|HOLD",
        "target_price": float,
        "stop_loss": float,
        "position_size": "1-2% portfolio",
        "reasoning": "Step-by-step analysis...",
        "key_factors": ["factor1", "factor2", "factor3"],
        "risk_level": "low"
    }},
    "balanced": {{...}},
    "aggressive": {{...}}
}}

Requirements:
- All prices must be specific numbers
- Reasoning must explain the chain of thought
- Key factors must be concrete and measurable
- Risk level must match variant type"""

    def _parse_strategy_response(
        self, response_text: str, current_price: float
    ) -> list[StrategyVariant]:
        """Parse LLM response into strategy variants.

        Args:
            response_text: Raw LLM response
            current_price: Current price for validation

        Returns:
            List of strategy variants
        """
        try:
            # Extract JSON from response
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            strategies = []
            for variant_name in ["conservative", "balanced", "aggressive"]:
                variant_data = data.get(variant_name, {})

                if variant_data.get("recommendation", "HOLD") == "HOLD":
                    continue

                strategy = StrategyVariant(
                    variant=variant_name,
                    recommendation=variant_data.get("recommendation", "HOLD"),
                    entry_price=current_price,
                    target_price=variant_data.get("target_price", current_price * 1.05),
                    stop_loss=variant_data.get("stop_loss", current_price * 0.95),
                    position_size=variant_data.get("position_size", "2% portfolio"),
                    reasoning=variant_data.get("reasoning", ""),
                    key_factors=variant_data.get("key_factors", []),
                    risk_level=variant_data.get("risk_level", "medium"),
                )
                strategies.append(strategy)

            return strategies

        except json.JSONDecodeError as e:
            print(f"Error parsing strategy response: {e}")
            return self._generate_default_strategies("UNKNOWN", current_price)

    def _generate_default_strategies(
        self, commodity: str, current_price: float
    ) -> list[StrategyVariant]:
        """Generate default strategies when LLM fails.

        Args:
            commodity: Commodity symbol
            current_price: Current price

        Returns:
            List of default strategies
        """
        return [
            StrategyVariant(
                variant="conservative",
                recommendation="BUY",
                entry_price=current_price,
                target_price=current_price * 1.03,
                stop_loss=current_price * 0.98,
                position_size="1-2% portfolio",
                reasoning="Default conservative strategy based on trend following",
                key_factors=["Price momentum", "Risk management"],
                risk_level="low",
            ),
            StrategyVariant(
                variant="balanced",
                recommendation="BUY",
                entry_price=current_price,
                target_price=current_price * 1.06,
                stop_loss=current_price * 0.97,
                position_size="2-3% portfolio",
                reasoning="Default balanced strategy with moderate risk/reward",
                key_factors=["Technical setup", "Market conditions"],
                risk_level="medium",
            ),
            StrategyVariant(
                variant="aggressive",
                recommendation="BUY",
                entry_price=current_price,
                target_price=current_price * 1.10,
                stop_loss=current_price * 0.95,
                position_size="3-5% portfolio",
                reasoning="Default aggressive strategy for high conviction setups",
                key_factors=["Breakout potential", "Momentum acceleration"],
                risk_level="high",
            ),
        ]

    def _assess_volatility(self, price_data: Any) -> str:
        """Assess volatility from price data.

        Args:
            price_data: Price data object

        Returns:
            Volatility assessment
        """
        if not price_data.close or len(price_data.close) < 10:
            return "medium"

        import numpy as np

        returns = [
            (price_data.close[i] / price_data.close[i - 1] - 1) * 100
            for i in range(1, len(price_data.close))
        ]
        volatility = np.std(returns)

        if volatility > 2:
            return "high"
        elif volatility > 1:
            return "medium"
        else:
            return "low"

    def _get_avg_sentiment(self, commodity: str) -> float:
        """Get average news sentiment.

        Args:
            commodity: Commodity symbol

        Returns:
            Average sentiment score
        """
        try:
            news = self.news_service.get_news_for_commodity(commodity, days=3, limit=10)
            if not news:
                return 0.0
            return sum(article.sentiment_score for article in news) / len(news)
        except Exception:
            return 0.0

    def _trigger_gemma4_analysis(
        self,
        commodity: str,
        strategies: list[dict[str, Any]],
        price_data: Any,
        news_summary: str,
    ) -> dict[str, Any]:
        """Trigger Gemma4 deep reasoning for low-confidence scenarios.

        Args:
            commodity: Commodity symbol
            strategies: Generated strategies
            price_data: Price data
            news_summary: News summary

        Returns:
            Gemma4 analysis results
        """
        try:
            # Build context for Gemma4
            context = f"""Commodity: {commodity}
Current Price: ${price_data.close[-1] if price_data.close else 0:,.2f}
Price Change (7d): {((price_data.close[-1] / price_data.close[-8] - 1) * 100) if len(price_data.close) >= 8 else 0:+.2f}%

Generated Strategies:
"""
            for s in strategies:
                strat = s["strategy"]
                context += f"- {strat.variant}: {strat.recommendation} (conf: {s['confidence_score']:.2f})\n"
                context += f"  Reasoning: {strat.reasoning[:200]}...\n"

            context += f"\nNews Context:\n{news_summary[:500]}"

            # Perform deep reasoning via DeepSeek
            result = self.llm_client.generate_insight(
                commodity=commodity,
                price_data={},
                news_summary=context,
            ).model_dump() if hasattr(self.llm_client, "generate_insight") else {}

            # If still uncertain, generate research task
            if result.get("needs_more_research"):
                research_task = {
                    "type": "low_confidence_investigation",
                    "commodity": commodity,
                    "current_price": price_data.close[-1] if price_data.close else 0,
                    "questions": result.get("evidence", []),
                    "recommended_action": "manual_review",
                }
                result["research_task"] = research_task

            return result

        except Exception as e:
            return {
                "error": str(e),
                "reasoning": "Failed to get Gemma4 analysis",
                "confidence": 0.0,
            }
