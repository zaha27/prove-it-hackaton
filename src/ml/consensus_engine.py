"""
Neuro-Symbolic Engine — XGBoost (Quant) → DeepSeek (Risk Manager).

Pipeline:
    Yahoo Finance News → XGBoost (technical prediction)
        → DeepSeek Reality Check (validates signal against macro news)
        → Final Trading Recommendation
"""

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DebateRound:
    """One pass: XGBoost quantitative signal + DeepSeek reality check."""
    round_number: int
    gemma4_argument: str          # XGBoost quantitative signal summary
    gemma4_sources: list[str] = field(default_factory=list)
    gemma4_position: dict = field(default_factory=dict)   # XGBoost position
    deepseek_critique: str = ""   # DeepSeek's macro analysis
    deepseek_counter: str = ""    # DeepSeek's final verdict
    deepseek_position: dict = field(default_factory=dict)
    agreement_score: float = 0.0


@dataclass
class ConsensusResult:
    """Final result of the neuro-symbolic pipeline."""
    commodity: str
    consensus_reached: bool
    rounds_conducted: int
    final_recommendation: str
    confidence: float
    direction: str       # "buy", "sell", "hold"
    risk_level: str      # "low", "medium", "high"
    debate_history: list[DebateRound] = field(default_factory=list)
    xgboost_input: dict = field(default_factory=dict)
    yahoo_news_summary: str = ""
    final_reasoning: str = ""
    gemma4_final_position: dict = field(default_factory=dict)   # XGBoost position
    deepseek_final_position: dict = field(default_factory=dict)  # DeepSeek position


_RISK_MANAGER_SYSTEM = (
    "You are an elite, institutional Macroeconomic Risk Manager.\n"
    "CRITICAL RULES:\n"
    "1. MAX LENGTH: You must respond in maximum 3 concise sentences. Be punchy and direct.\n"
    "2. USER ALIGNMENT: You MUST strictly obey the user's Risk Profile and Investment Horizon.\n"
    "3. NO SHORTING FOR HODLERS: If the user has a Long-Term horizon (Years/HODL), NEVER recommend short-term trading or 'Short' positions. "
    "Advise to 'ACCUMULATE', 'HOLD', or 'REDUCE EXPOSURE'.\n"
    "4. OVERRIDE: If the XGBoost signal is risky but the user is Conservative, OVERRIDE the signal and recommend HOLD.\n"
    "You must briefly justify your call based on their profile.\n"
    "Always respond in valid JSON."
)


class ConsensusEngine:
    """Neuro-Symbolic pipeline: XGBoost (Quant) validated by DeepSeek (Risk Manager)."""

    def __init__(
        self,
        max_rounds: int = 5,
        agreement_threshold: float = 0.8,
        gemini_mcp=None,   # kept for API compat, unused
    ):
        self.agreement_threshold = agreement_threshold
        self._api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self._base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self._model = "deepseek-chat"
        self._max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # ── Public ────────────────────────────────────────────────────────────────

    async def reach_consensus(
        self,
        commodity: str,
        xgboost_result: dict,
        price_data: dict,
        yahoo_news: list[dict],
        user_profile: dict | None = None,
        # Legacy compat
        risk_profile: str = "Balanced",
    ) -> ConsensusResult:
        """
        Run XGBoost → DeepSeek Reality Check and return a ConsensusResult.

        XGBoost provides the quantitative signal (prediction %, confidence, top features).
        DeepSeek validates it against macro news context.
        """
        logger.info("Neuro-Symbolic pipeline starting for %s", commodity)

        # Resolve profile — dict takes precedence over legacy string
        profile = user_profile or {}
        if not profile and risk_profile != "Balanced":
            _str_to_score = {"Conservative": 2, "Balanced": 3, "Aggressive": 4}
            s = _str_to_score.get(risk_profile, 3)
            profile = {"risk_score": s, "investment_horizon": 3, "market_familiarity": 3}

        yahoo_summary = self._summarize_yahoo_news(yahoo_news)
        xgboost_summary = self._format_xgboost_result(xgboost_result)

        # --- XGBoost position (The Quant) ---
        # Apply user risk profile to XGBoost confidence threshold
        from data.user_manager import UserManager
        xgb_threshold = UserManager.get_xgb_confidence_threshold(profile)

        xgb_direction = self._xgboost_to_direction(xgboost_result, threshold=xgb_threshold)
        xgb_confidence = float(xgboost_result.get("confidence", 0.5))
        xgb_prediction_pct = float(xgboost_result.get("prediction", 0))

        quant_argument = (
            f"XGBoost Quantitative Signal — {commodity}\n"
            f"Direction: {xgb_direction.upper()}\n"
            f"Predicted change: {xgb_prediction_pct:+.2%}\n"
            f"Model confidence: {xgb_confidence:.0%}  "
            f"(threshold for this user: {xgb_threshold:.0%})\n\n"
            f"Technical breakdown:\n{xgboost_summary}"
        )
        quant_position = {
            "direction": xgb_direction,
            "confidence": int(xgb_confidence * 100),
            "risk_level": "medium",
        }

        # --- DeepSeek Reality Check (The Risk Manager) ---
        ds_response = await self._deepseek_reality_check(
            commodity=commodity,
            xgboost_summary=xgboost_summary,
            yahoo_summary=yahoo_summary,
            price_data=price_data,
            xgb_direction=xgb_direction,
            xgb_confidence=xgb_confidence,
            user_profile=profile,
        )

        ds_position = ds_response.get("position", {})
        final_direction = ds_response.get("final_direction", xgb_direction)
        final_confidence = float(ds_response.get("confidence", xgb_confidence))

        # Agreement: does DeepSeek validate XGBoost's direction?
        direction_match = ds_position.get("direction", final_direction) == xgb_direction
        agreement_score = 0.9 if direction_match else 0.4
        consensus_reached = direction_match

        debate_round = DebateRound(
            round_number=1,
            gemma4_argument=quant_argument,
            gemma4_sources=[],
            gemma4_position=quant_position,
            deepseek_critique=ds_response.get("critique", ""),
            deepseek_counter=ds_response.get("final_recommendation", final_direction.upper()),
            deepseek_position=ds_position,
            agreement_score=agreement_score,
        )

        logger.info(
            "Pipeline complete for %s: %s (confidence %.0f%%, consensus=%s)",
            commodity, final_direction.upper(), final_confidence * 100, consensus_reached,
        )

        return ConsensusResult(
            commodity=commodity,
            consensus_reached=consensus_reached,
            rounds_conducted=1,
            final_recommendation=ds_response.get("final_recommendation", final_direction.upper()),
            confidence=final_confidence,
            direction=final_direction,
            risk_level=ds_position.get("risk_level", "medium"),
            debate_history=[debate_round],
            xgboost_input=xgboost_result,
            yahoo_news_summary=yahoo_summary,
            final_reasoning=ds_response.get("reasoning", ""),
            gemma4_final_position=quant_position,
            deepseek_final_position=ds_position,
        )

    # ── Private ────────────────────────────────────────────────────────────────

    async def _deepseek_reality_check(
        self,
        commodity: str,
        xgboost_summary: str,
        yahoo_summary: str,
        price_data: dict,
        xgb_direction: str,
        xgb_confidence: float,
        user_profile: dict | None = None,
        # legacy kept for compat
        risk_profile: str = "Balanced",
    ) -> dict:
        """Call DeepSeek to validate the XGBoost signal against macro news."""

        current_price = price_data.get("current_price", price_data.get("current", "N/A"))
        change_24h = price_data.get("change_24h", price_data.get("change_24h_pct", "N/A"))

        # Build granular user context for DeepSeek prompt
        profile = user_profile or {}
        from data.user_manager import UserManager
        risk_instruction = UserManager.get_deepseek_context(profile)

        prompt = f"""## USER RISK PROFILE (HIGHEST PRIORITY)
{risk_instruction}

## XGBoost Quantitative Model — {commodity}
{xgboost_summary}

The model signals: **{xgb_direction.upper()}** with {xgb_confidence:.0%} confidence.

## Current Price Context
- Price: ${current_price}
- 24h change: {change_24h}%

## Recent News & Macro Context
{yahoo_summary}

## Your Task
Does the macro/news context VALIDATE or CONTRADICT the XGBoost {xgb_direction.upper()} signal?

Analyze:
1. News sentiment alignment with the quantitative signal
2. Any macro factors (geopolitics, supply shocks, rate decisions) that override the technical signal
3. Your final validated recommendation, adjusted for the user's risk profile

Respond ONLY with valid JSON:
{{
    "critique": "Your analysis of XGBoost signal vs macro context (2-3 sentences)",
    "final_recommendation": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
    "final_direction": "buy|sell|hold",
    "confidence": 0.0,
    "reasoning": "One concise sentence explaining your final call",
    "position": {{
        "direction": "buy|sell|hold",
        "confidence": 0,
        "risk_level": "low|medium|high"
    }}
}}"""

        import asyncio
        loop = asyncio.get_event_loop()

        def _call() -> str:
            if not self._api_key:
                raise ValueError("DEEPSEEK_API_KEY not configured")
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            resp = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _RISK_MANAGER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self._max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""

        try:
            raw = await loop.run_in_executor(None, _call)
        except Exception as exc:
            logger.error("DeepSeek reality check failed for %s: %s", commodity, exc)
            return self._fallback_response(xgb_direction, xgb_confidence, str(exc))

        # Parse JSON
        try:
            text = raw.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("DeepSeek returned non-JSON for %s, using raw text", commodity)
            return {
                "critique": raw[:500],
                "final_recommendation": xgb_direction.upper(),
                "final_direction": xgb_direction,
                "confidence": xgb_confidence,
                "reasoning": "DeepSeek response parsed from free text.",
                "position": {
                    "direction": xgb_direction,
                    "confidence": int(xgb_confidence * 100),
                    "risk_level": "medium",
                },
            }

    def _fallback_response(self, direction: str, confidence: float, error: str) -> dict:
        return {
            "critique": f"DeepSeek unavailable ({error}). Falling back to XGBoost signal only.",
            "final_recommendation": direction.upper(),
            "final_direction": direction,
            "confidence": confidence * 0.7,  # Lower confidence without validation
            "reasoning": "XGBoost signal used without macro validation (DeepSeek unavailable).",
            "position": {
                "direction": direction,
                "confidence": int(confidence * 70),
                "risk_level": "high",  # Higher risk without macro check
            },
        }

    def _xgboost_to_direction(self, result: dict, threshold: float = 0.70) -> str:
        """
        Convert XGBoost output to direction.
        Respects user risk profile: conservative users need higher confidence
        before the model issues a directional signal.
        """
        prediction = float(result.get("prediction", 0))
        confidence = float(result.get("confidence", 0))

        # If model confidence is below the user's threshold, default to HOLD
        if confidence < threshold:
            return "hold"

        if prediction > 0.005:
            return "buy"
        elif prediction < -0.005:
            return "sell"
        return "hold"

    def _summarize_yahoo_news(self, news: list[dict]) -> str:
        if not news:
            return "No recent news available."
        parts = []
        total_sentiment = 0.0
        for i, article in enumerate(news[:5], 1):
            sentiment = article.get("sentiment", "neutral")
            score = float(article.get("sentiment_score", 0))
            total_sentiment += score
            parts.append(f"{i}. [{sentiment.upper()}] {article.get('title', '')}")
        avg = total_sentiment / len(news) if news else 0.0
        overall = "positive" if avg > 0.05 else "negative" if avg < -0.05 else "neutral"
        return (
            f"Overall Sentiment: {overall.upper()} (score: {avg:.3f}) | {len(news)} articles\n"
            + "\n".join(parts)
        )

    def _format_xgboost_result(self, result: dict) -> str:
        prediction = float(result.get("prediction", 0))
        confidence = float(result.get("confidence", 0))
        reasoning = result.get("reasoning", "No reasoning provided")
        top_features = result.get("top_features", [])[:5]
        features_str = "\n".join(
            f"  - {f.get('name', 'unknown')}: {f.get('value', 0):.4f} ({f.get('impact', 'neutral')})"
            for f in top_features
        )
        return (
            f"Prediction: {prediction:+.2%}\n"
            f"Confidence: {confidence:.0%}\n"
            f"Reasoning: {reasoning}\n"
            f"Top Features:\n{features_str}"
        )
