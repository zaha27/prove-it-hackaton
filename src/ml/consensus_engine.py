"""Consensus Engine - DeepSeek + Gemma4 debate loop for trading decisions."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from src.rl.ollama_client import OllamaClient
from src.data.clients.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


@dataclass
class DebateRound:
    """Single round of debate between agents."""
    round_number: int
    gemma4_argument: str
    gemma4_sources: list[str] = field(default_factory=list)
    gemma4_position: dict = field(default_factory=dict)
    deepseek_critique: str = ""
    deepseek_counter: str = ""
    deepseek_position: dict = field(default_factory=dict)
    agreement_score: float = 0.0


@dataclass
class ConsensusResult:
    """Final result of consensus process."""
    commodity: str
    consensus_reached: bool
    rounds_conducted: int
    final_recommendation: str
    confidence: float
    direction: str  # "buy", "sell", "hold"
    risk_level: str  # "low", "medium", "high"
    debate_history: list[DebateRound] = field(default_factory=list)
    xgboost_input: dict = field(default_factory=dict)
    yahoo_news_summary: str = ""
    final_reasoning: str = ""
    gemma4_final_position: dict = field(default_factory=dict)
    deepseek_final_position: dict = field(default_factory=dict)


class ConsensusEngine:
    """DeepSeek + Gemma4 debate loop until agreement on trading decisions."""

    def __init__(
        self,
        max_rounds: int = 5,
        agreement_threshold: float = 0.8,
        gemini_mcp=None,  # Will be injected
    ):
        self.max_rounds = max_rounds
        self.agreement_threshold = agreement_threshold
        self.ollama = OllamaClient()  # Gemma4
        self.deepseek = DeepSeekClient()
        self.gemini_mcp = gemini_mcp

    async def reach_consensus(
        self,
        commodity: str,
        xgboost_result: dict,
        price_data: dict,
        yahoo_news: list[dict],
    ) -> ConsensusResult:
        """
        Run debate loop between DeepSeek and Gemma4 until consensus.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")
            xgboost_result: XGBoost prediction with features
            price_data: Current price data
            yahoo_news: Yahoo Finance news articles with sentiment

        Returns:
            ConsensusResult with debate history and final recommendation
        """
        logger.info(f"Starting consensus debate for {commodity}")

        # Prepare initial context
        yahoo_summary = self._summarize_yahoo_news(yahoo_news)
        xgboost_summary = self._format_xgboost_result(xgboost_result)

        # Initialize debate
        debate_history: list[DebateRound] = []
        gemma4_position: dict | None = None
        deepseek_position: dict | None = None

        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"  Debate Round {round_num}/{self.max_rounds}")

            # Gemma4's turn (with web search via Gemini MCP)
            gemma4_response = await self._gemma4_turn(
                round_num=round_num,
                commodity=commodity,
                xgboost_summary=xgboost_summary,
                yahoo_summary=yahoo_summary,
                price_data=price_data,
                previous_deepseek_critique=deepseek_position.get("critique", "") if deepseek_position else "",
            )

            gemma4_position = gemma4_response["position"]

            # DeepSeek's turn (critique)
            deepseek_response = await self._deepseek_turn(
                round_num=round_num,
                commodity=commodity,
                xgboost_summary=xgboost_summary,
                yahoo_summary=yahoo_summary,
                price_data=price_data,
                gemma4_proposal=gemma4_response,
                previous_rounds=debate_history,
            )

            deepseek_position = deepseek_response["position"]

            # Record this round
            agreement_score = self._calculate_agreement(
                gemma4_position, deepseek_position
            )

            debate_round = DebateRound(
                round_number=round_num,
                gemma4_argument=gemma4_response["argument"],
                gemma4_sources=gemma4_response.get("sources", []),
                gemma4_position=gemma4_position,
                deepseek_critique=deepseek_response["critique"],
                deepseek_counter=deepseek_response["counter_argument"],
                deepseek_position=deepseek_position,
                agreement_score=agreement_score,
            )
            debate_history.append(debate_round)

            logger.info(f"    Agreement score: {agreement_score:.2f}")

            # Check for consensus
            if agreement_score >= self.agreement_threshold:
                logger.info(f"  Consensus reached in round {round_num}")
                consensus_reached = True
                break
        else:
            # Max rounds reached without consensus
            logger.info(f"  Max rounds reached without full consensus")
            consensus_reached = False

        # Generate final recommendation
        final_result = await self._generate_final_recommendation(
            commodity=commodity,
            debate_history=debate_history,
            xgboost_result=xgboost_result,
            yahoo_summary=yahoo_summary,
        )

        return ConsensusResult(
            commodity=commodity,
            consensus_reached=consensus_reached,
            rounds_conducted=len(debate_history),
            final_recommendation=final_result["recommendation"],
            confidence=final_result["confidence"],
            direction=final_result["direction"],
            risk_level=final_result["risk_level"],
            debate_history=debate_history,
            xgboost_input=xgboost_result,
            yahoo_news_summary=yahoo_summary,
            final_reasoning=final_result["reasoning"],
            gemma4_final_position=gemma4_position or {},
            deepseek_final_position=deepseek_position or {},
        )

    async def _gemma4_turn(
        self,
        round_num: int,
        commodity: str,
        xgboost_summary: str,
        yahoo_summary: str,
        price_data: dict,
        previous_deepseek_critique: str,
    ) -> dict:
        """Gemma4's turn - analyze and propose with web search."""

        # Build prompt for Gemma4
        if round_num == 1:
            prompt = f"""You are Gemma4, an AI trading analyst. Analyze the following data for {commodity} and propose an initial trading position.

## Data Summary

**XGBoost Technical Analysis:**
{xgboost_summary}

**Yahoo Finance News Summary:**
{yahoo_summary}

**Current Price Data:**
- Current Price: ${price_data.get('current', 'N/A')}
- 24h Change: {price_data.get('change_24h_pct', 'N/A')}%
- 7d Change: {price_data.get('change_7d_pct', 'N/A')}%

## Your Task

1. Search the web for current {commodity} market news and trends (use your knowledge)
2. Analyze the XGBoost technical indicators
3. Consider the Yahoo Finance news sentiment
4. Propose a trading position with clear reasoning

Respond in JSON format:
{{
    "argument": "Your detailed reasoning here...",
    "sources": ["source1", "source2"],
    "position": {{
        "direction": "buy|sell|hold",
        "confidence": 0-100,
        "risk_level": "low|medium|high",
        "time_horizon": "short|medium|long",
        "key_factors": ["factor1", "factor2"]
    }}
}}"""
        else:
            prompt = f"""You are Gemma4, responding to DeepSeek's critique in round {round_num}.

## Your Previous Position
{xgboost_summary}

## DeepSeek's Critique
{previous_deepseek_critique}

## Your Task

Address DeepSeek's concerns and either:
1. Defend your position with additional evidence (search web if needed)
2. Revise your position based on valid critiques

Respond in JSON format:
{{
    "argument": "Your rebuttal and reasoning...",
    "sources": ["source1"],
    "position": {{
        "direction": "buy|sell|hold",
        "confidence": 0-100,
        "risk_level": "low|medium|high",
        "time_horizon": "short|medium|long",
        "key_factors": ["factor1"]
    }}
}}"""

        # Call Gemma4 via Ollama with Gemini MCP web search grounding
        if self.gemini_mcp:
            # Use web search enhanced generation
            search_query = f"{commodity} commodity market news analysis latest"
            gemma_result = self.ollama.generate_with_grounding(
                prompt=prompt,
                system="You are Gemma4, an expert commodity trading analyst. Use web search knowledge to inform your analysis. Always respond in valid JSON format.",
                search_query=search_query,
                gemini_mcp=self.gemini_mcp,
            )
            response = gemma_result["response"]
            sources = gemma_result.get("sources", [])
        else:
            # Fallback to regular generation
            response = self.ollama.generate(
                prompt=prompt,
                system="You are Gemma4, an expert commodity trading analyst. Always respond in valid JSON format.",
            )
            sources = []

        # Parse JSON response
        try:
            result = json.loads(response)
            # Add sources from web search if available
            if sources:
                result["sources"] = sources
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "argument": response[:500],
                "sources": sources if sources else [],
                "position": {
                    "direction": "hold",
                    "confidence": 50,
                    "risk_level": "medium",
                    "time_horizon": "medium",
                    "key_factors": ["uncertainty"],
                },
            }

        return result

    async def _deepseek_turn(
        self,
        round_num: int,
        commodity: str,
        xgboost_summary: str,
        yahoo_summary: str,
        price_data: dict,
        gemma4_proposal: dict,
        previous_rounds: list[DebateRound],
    ) -> dict:
        """DeepSeek's turn - critique Gemma4's proposal."""

        prompt = f"""You are DeepSeek, a critical trading analyst. Critique Gemma4's proposal for {commodity}.

## Context

**XGBoost Technical Analysis:**
{xgboost_summary}

**Yahoo Finance News:**
{yahoo_summary}

**Current Price:** ${price_data.get('current', 'N/A')} (24h: {price_data.get('change_24h_pct', 'N/A')}%)

## Gemma4's Proposal (Round {round_num})

**Argument:**
{gemma4_proposal.get('argument', 'No argument provided')}

**Position:**
- Direction: {gemma4_proposal.get('position', {}).get('direction', 'unknown')}
- Confidence: {gemma4_proposal.get('position', {}).get('confidence', 'unknown')}%
- Risk Level: {gemma4_proposal.get('position', {}).get('risk_level', 'unknown')}

## Your Task

1. Critically analyze Gemma4's argument
2. Identify any logical flaws, missing factors, or biases
3. Provide your counter-argument
4. State your own position

Be thorough but constructive. Your goal is to reach the best trading decision through debate.

Respond in JSON format:
{{
    "critique": "Your critique of Gemma4's argument...",
    "counter_argument": "Your counter-argument and reasoning...",
    "position": {{
        "direction": "buy|sell|hold",
        "confidence": 0-100,
        "risk_level": "low|medium|high",
        "critique": "Summary of your critique"
    }}
}}"""

        # Call DeepSeek API
        response = self.deepseek.generate(
            prompt=prompt,
            system="You are DeepSeek, a critical and thorough trading analyst. Your role is to challenge assumptions and ensure robust decision-making. Always respond in valid JSON format.",
        )

        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback
            result = {
                "critique": "Unable to parse response",
                "counter_argument": response[:500],
                "position": {
                    "direction": "hold",
                    "confidence": 50,
                    "risk_level": "medium",
                    "critique": "uncertainty",
                },
            }

        return result

    def _calculate_agreement(
        self, gemma4_pos: dict, deepseek_pos: dict
    ) -> float:
        """Calculate agreement score between two positions."""
        # Direction match (0 or 1)
        direction_match = (
            1.0
            if gemma4_pos.get("direction") == deepseek_pos.get("direction")
            else 0.0
        )

        # Confidence similarity (1 - normalized difference)
        gemma4_conf = gemma4_pos.get("confidence", 50)
        deepseek_conf = deepseek_pos.get("confidence", 50)
        confidence_sim = 1.0 - abs(gemma4_conf - deepseek_conf) / 100.0

        # Risk level match
        risk_match = (
            1.0
            if gemma4_pos.get("risk_level") == deepseek_pos.get("risk_level")
            else 0.0
        )

        # Weighted average
        agreement = (direction_match * 0.5 + confidence_sim * 0.3 + risk_match * 0.2)

        return agreement

    async def _generate_final_recommendation(
        self,
        commodity: str,
        debate_history: list[DebateRound],
        xgboost_result: dict,
        yahoo_summary: str,
    ) -> dict:
        """Generate final trading recommendation after debate."""

        # Get last positions
        last_round = debate_history[-1] if debate_history else None

        if not last_round:
            return {
                "recommendation": "HOLD",
                "confidence": 0.5,
                "direction": "hold",
                "risk_level": "medium",
                "reasoning": "No debate occurred",
            }

        # If consensus reached, use agreed position
        if last_round.agreement_score >= self.agreement_threshold:
            direction = last_round.gemma4_position.get("direction", "hold")
            confidence = (
                last_round.gemma4_position.get("confidence", 50)
                + last_round.deepseek_position.get("confidence", 50)
            ) / 200.0  # Average and normalize

            return {
                "recommendation": direction.upper(),
                "confidence": confidence,
                "direction": direction,
                "risk_level": last_round.gemma4_position.get("risk_level", "medium"),
                "reasoning": f"Consensus reached with {last_round.agreement_score:.0%} agreement. Both agents agree on {direction}.",
            }

        # No consensus - synthesize both views
        prompt = f"""Synthesize the following debate into a final trading recommendation for {commodity}.

## Debate Summary

**XGBoost Analysis:**
{self._format_xgboost_result(xgboost_result)}

**Yahoo News:**
{yahoo_summary}

**Final Positions:**
- Gemma4: {last_round.gemma4_position.get('direction', 'unknown')} ({last_round.gemma4_position.get('confidence', 0)}% confidence)
- DeepSeek: {last_round.deepseek_position.get('direction', 'unknown')} ({last_round.deepseek_position.get('confidence', 0)}% confidence)

## Your Task

Provide a balanced final recommendation considering both perspectives.

Respond in JSON format:
{{
    "recommendation": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
    "confidence": 0-1,
    "direction": "buy|sell|hold",
    "risk_level": "low|medium|high",
    "reasoning": "Detailed explanation..."
}}"""

        response = self.deepseek.generate(
            prompt=prompt,
            system="You are a senior trading strategist synthesizing multiple AI analyses into a final recommendation.",
        )

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback synthesis
            gemma4_dir = last_round.gemma4_position.get("direction", "hold")
            deepseek_dir = last_round.deepseek_position.get("direction", "hold")

            if gemma4_dir == deepseek_dir:
                direction = gemma4_dir
                confidence = 0.7
            else:
                direction = "hold"
                confidence = 0.5

            result = {
                "recommendation": direction.upper(),
                "confidence": confidence,
                "direction": direction,
                "risk_level": "medium",
                "reasoning": f"No consensus reached. Gemma4: {gemma4_dir}, DeepSeek: {deepseek_dir}. Defaulting to cautious position.",
            }

        return result

    def _summarize_yahoo_news(self, news: list[dict]) -> str:
        """Summarize Yahoo Finance news for the prompt."""
        if not news:
            return "No recent news available."

        summary_parts = []
        total_sentiment = 0

        for i, article in enumerate(news[:5], 1):
            title = article.get("title", "")
            sentiment = article.get("sentiment", "neutral")
            score = article.get("sentiment_score", 0)
            total_sentiment += score

            summary_parts.append(f"{i}. [{sentiment.upper()}] {title}")

        avg_sentiment = total_sentiment / len(news) if news else 0

        overall = "positive" if avg_sentiment > 0.05 else "negative" if avg_sentiment < -0.05 else "neutral"

        return f"""Overall Sentiment: {overall.upper()} (score: {avg_sentiment:.3f})
Articles: {len(news)}

Top Headlines:
{chr(10).join(summary_parts)}"""

    def _format_xgboost_result(self, result: dict) -> str:
        """Format XGBoost result for prompts."""
        prediction = result.get("prediction", 0)
        confidence = result.get("confidence", 0)
        reasoning = result.get("reasoning", "No reasoning provided")

        top_features = result.get("top_features", [])[:5]
        features_str = "\n".join([
            f"  - {f.get('name', 'unknown')}: {f.get('value', 0):.4f} ({f.get('impact', 'neutral')})"
            for f in top_features
        ])

        return f"""Prediction: {prediction:+.2%}
Confidence: {confidence:.0%}

Reasoning: {reasoning}

Top Features:
{features_str}"""
