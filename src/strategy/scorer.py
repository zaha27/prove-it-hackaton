"""Confidence scoring for strategies."""

from typing import Any

import numpy as np


class ConfidenceScorer:
    """Calculates confidence scores for strategies."""

    def __init__(self) -> None:
        """Initialize the confidence scorer."""
        pass

    def calculate_score(
        self,
        backtest_metrics: dict[str, Any],
        pattern_similarity: float,
        rl_success_rate: float = 0.5,
    ) -> float:
        """Calculate overall confidence score.

        Args:
            backtest_metrics: Backtest metrics
            pattern_similarity: Average pattern similarity
            rl_success_rate: RL success rate for similar strategies

        Returns:
            Confidence score between 0 and 1
        """
        # Component weights
        weights = {
            "performance": 0.30,
            "risk": 0.25,
            "consistency": 0.20,
            "similarity": 0.15,
            "rl_history": 0.10,
        }

        scores = {}

        # Performance score (win rate + expectancy)
        win_rate = backtest_metrics.get("win_rate", 0)
        expectancy = backtest_metrics.get("expectancy", 0)
        sharpe = backtest_metrics.get("sharpe_ratio", 0)

        perf_score = (
            (win_rate / 0.70) * 0.4 +  # Optimal win rate ~70%
            (min(expectancy, 10) / 10) * 0.3 +  # Cap at 10%
            (min(sharpe, 2.0) / 2.0) * 0.3  # Cap at Sharpe 2.0
        )
        scores["performance"] = min(perf_score, 1.0)

        # Risk score (inverse of drawdown + VaR)
        max_dd = abs(backtest_metrics.get("max_drawdown", 0))
        var_95 = abs(backtest_metrics.get("var_95", 0))

        risk_score = (
            (1 - min(max_dd / 20, 1)) * 0.5 +  # Max DD 20% = 0 score
            (1 - min(var_95 / 10, 1)) * 0.5  # VaR 10% = 0 score
        )
        scores["risk"] = max(risk_score, 0)

        # Consistency score (profit factor + sample size)
        profit_factor = backtest_metrics.get("profit_factor", 1)
        sample_size = backtest_metrics.get("sample_size", 0)

        consistency_score = (
            (min(profit_factor, 3) / 3) * 0.6 +  # Cap at PF 3.0
            (min(sample_size, 100) / 100) * 0.4  # Cap at 100 samples
        )
        scores["consistency"] = min(consistency_score, 1.0)

        # Similarity score (direct)
        scores["similarity"] = pattern_similarity

        # RL history score
        scores["rl_history"] = rl_success_rate

        # Calculate weighted score
        confidence = sum(
            scores.get(component, 0) * weight
            for component, weight in weights.items()
        )

        return min(max(confidence, 0.0), 1.0)

    def calculate_tier(self, confidence_score: float) -> str:
        """Calculate confidence tier.

        Args:
            confidence_score: Confidence score

        Returns:
            Tier name
        """
        if confidence_score >= 0.80:
            return "high"
        elif confidence_score >= 0.60:
            return "medium"
        elif confidence_score >= 0.40:
            return "low"
        else:
            return "reject"

    def get_score_breakdown(
        self,
        backtest_metrics: dict[str, Any],
        pattern_similarity: float,
        rl_success_rate: float = 0.5,
    ) -> dict[str, Any]:
        """Get detailed score breakdown.

        Args:
            backtest_metrics: Backtest metrics
            pattern_similarity: Pattern similarity
            rl_success_rate: RL success rate

        Returns:
            Score breakdown
        """
        total_score = self.calculate_score(
            backtest_metrics, pattern_similarity, rl_success_rate
        )

        return {
            "total_score": total_score,
            "tier": self.calculate_tier(total_score),
            "components": {
                "performance": {
                    "win_rate": backtest_metrics.get("win_rate", 0),
                    "expectancy": backtest_metrics.get("expectancy", 0),
                    "sharpe": backtest_metrics.get("sharpe_ratio", 0),
                },
                "risk": {
                    "max_drawdown": backtest_metrics.get("max_drawdown", 0),
                    "var_95": backtest_metrics.get("var_95", 0),
                },
                "consistency": {
                    "profit_factor": backtest_metrics.get("profit_factor", 0),
                    "sample_size": backtest_metrics.get("sample_size", 0),
                },
                "similarity": pattern_similarity,
                "rl_history": rl_success_rate,
            },
        }

    def compare_scores(
        self, scores: list[tuple[str, float]]
    ) -> dict[str, Any]:
        """Compare multiple strategy scores.

        Args:
            scores: List of (strategy_name, score) tuples

        Returns:
            Comparison results
        """
        if not scores:
            return {"best": None, "rankings": []}

        # Sort by score
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # Calculate statistics
        score_values = [s[1] for s in scores]

        return {
            "best": sorted_scores[0],
            "rankings": sorted_scores,
            "average": np.mean(score_values),
            "std_dev": np.std(score_values),
            "spread": sorted_scores[0][1] - sorted_scores[-1][1],
        }
