"""Weighted RAG retriever for RL-augmented context."""

from typing import Any

from sentence_transformers import SentenceTransformer

from src.data.config import config
from src.data.ingestion.prediction_tracker import PredictionTracker


class WeightedRAGRetriever:
    """Retrieves context with RL-based weighting."""

    def __init__(self) -> None:
        """Initialize the weighted RAG retriever."""
        self.prediction_tracker = PredictionTracker()
        self.embedding_model = SentenceTransformer(config.embedding_model)

    def retrieve_context(
        self,
        query: str,
        commodity: str,
        top_k: int = 5,
        min_success_rate: float = 0.5,
    ) -> dict[str, Any]:
        """Retrieve weighted context for LLM prompting.

        Args:
            query: Query text (current reasoning)
            commodity: Commodity symbol
            top_k: Number of examples to retrieve
            min_success_rate: Minimum success rate filter

        Returns:
            Weighted context
        """
        # Find similar successful predictions
        similar = self.prediction_tracker.find_similar_successful_predictions(
            query, commodity, top_k=top_k * 2  # Get more to filter
        )

        # Filter by success rate and weight
        weighted_context = []
        for pred in similar:
            # Calculate weight based on similarity and return
            weight = pred.get("weight", 0.5)
            actual_return = pred.get("actual_return", 0)

            # Boost weight for high returns
            if actual_return > 5:
                weight *= 1.5
            elif actual_return > 2:
                weight *= 1.2

            weighted_context.append({
                "reasoning": pred.get("reasoning", ""),
                "actual_return": actual_return,
                "weight": weight,
                "similarity": pred.get("similarity", 0),
            })

        # Sort by weight and take top_k
        weighted_context.sort(key=lambda x: x["weight"], reverse=True)
        top_contexts = weighted_context[:top_k]

        # Format for LLM prompt
        context_text = self._format_context(top_contexts)

        return {
            "context_text": context_text,
            "contexts": top_contexts,
            "avg_historical_return": sum(
                c["actual_return"] for c in top_contexts
            ) / len(top_contexts) if top_contexts else 0,
        }

    def _format_context(self, contexts: list[dict[str, Any]]) -> str:
        """Format contexts for LLM prompt.

        Args:
            contexts: List of context items

        Returns:
            Formatted context string
        """
        if not contexts:
            return ""

        lines = ["\n### Historically Successful Similar Strategies\n"]

        for i, ctx in enumerate(contexts, 1):
            lines.append(f"{i}. Historical Strategy (Return: {ctx['actual_return']:+.1f}%)")
            lines.append(f"   Reasoning: {ctx['reasoning'][:150]}...")
            lines.append(f"   Relevance Score: {ctx['weight']:.2f}")
            lines.append("")

        return "\n".join(lines)

    def get_reasoning_guidance(
        self, commodity: str, current_sentiment: str
    ) -> dict[str, Any]:
        """Get guidance for reasoning based on historical success.

        Args:
            commodity: Commodity symbol
            current_sentiment: Current market sentiment

        Returns:
            Reasoning guidance
        """
        # Get successful patterns
        successful = self.prediction_tracker.get_successful_reasoning_patterns(
            commodity, top_k=10
        )

        # Analyze common factors in successful predictions
        factors = self._extract_common_factors(successful)

        # Get warnings from failed predictions
        warnings = self._get_failure_warnings(commodity)

        return {
            "recommended_factors": factors,
            "warnings": warnings,
            "successful_examples": successful[:3],
        }

    def _extract_common_factors(
        self, patterns: list[dict[str, Any]]
    ) -> list[str]:
        """Extract common factors from successful patterns.

        Args:
            patterns: List of successful patterns

        Returns:
            List of common factors
        """
        # This is a simplified implementation
        # In production, use NLP to extract and cluster factors

        all_factors = []
        for pattern in patterns:
            # Extract factors from reasoning (simplified)
            reasoning = pattern.get("reasoning", "")
            # Look for keywords indicating factors
            if "inflation" in reasoning.lower():
                all_factors.append("inflation hedge demand")
            if "central bank" in reasoning.lower():
                all_factors.append("central bank policy")
            if "supply" in reasoning.lower():
                all_factors.append("supply constraints")
            if "demand" in reasoning.lower():
                all_factors.append("demand growth")

        # Count and return top factors
        from collections import Counter
        factor_counts = Counter(all_factors)
        return [factor for factor, _ in factor_counts.most_common(5)]

    def _get_failure_warnings(self, commodity: str) -> list[str]:
        """Get warnings based on failed predictions.

        Args:
            commodity: Commodity symbol

        Returns:
            List of warnings
        """
        # This would query for failed predictions and extract lessons
        # Simplified implementation
        return [
            "Avoid over-reliance on single news events",
            "Consider broader market context",
            "Watch for false breakouts",
        ]

    def build_enhanced_prompt(
        self,
        base_prompt: str,
        commodity: str,
        query: str,
    ) -> str:
        """Build an enhanced prompt with RL context.

        Args:
            base_prompt: Base prompt
            commodity: Commodity symbol
            query: Query text

        Returns:
            Enhanced prompt
        """
        # Retrieve weighted context
        context = self.retrieve_context(query, commodity)

        # Get reasoning guidance
        guidance = self.get_reasoning_guidance(commodity, "neutral")

        # Build enhanced prompt
        enhanced = f"""{base_prompt}

## Learning from Historical Performance

Based on analysis of {len(context.get('contexts', []))} similar past strategies:
- Average historical return: {context.get('avg_historical_return', 0):+.1f}%

{context.get('context_text', '')}

## Recommended Analysis Factors
{chr(10).join(f"- {factor}" for factor in guidance.get('recommended_factors', []))}

## Cautionary Notes
{chr(10).join(f"- {warning}" for warning in guidance.get('warnings', []))}

Use these insights to improve your strategy while adapting to current market conditions.
"""

        return enhanced
