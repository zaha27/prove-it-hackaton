"""Backtesting engine for strategy validation."""

from typing import Any

from src.backtest.metrics import calculate_all_metrics, passes_thresholds
from src.backtest.simulator import PatternSimulator
from src.data.config import config


class BacktestEngine:
    """Engine for backtesting trading strategies."""

    def __init__(self) -> None:
        """Initialize the backtesting engine."""
        self.simulator = PatternSimulator()
        self.config = config

    def backtest_strategy(
        self,
        commodity: str,
        current_prices: list[float],
        current_volumes: list[int],
        strategy: dict[str, Any],
    ) -> dict[str, Any]:
        """Backtest a strategy against historical patterns.

        Args:
            commodity: Commodity symbol
            current_prices: Current price series
            current_volumes: Current volume series
            strategy: Strategy definition

        Returns:
            Backtest results with metrics and validation status
        """
        # Run simulation
        results = self.simulator.simulate_strategy(
            commodity=commodity,
            current_prices=current_prices,
            current_volumes=current_volumes,
            strategy=strategy,
            min_sample_size=self.config.backtest_min_sample_size,
        )

        if not results.get("valid", False):
            return {
                "valid": False,
                "status": "rejected",
                "error": results.get("error", "Unknown error"),
                "sample_size": results.get("sample_size", 0),
            }

        # Check thresholds
        passes, failures = passes_thresholds(results, self.config)

        return {
            "valid": True,
            "status": "validated" if passes else "rejected",
            "metrics": results,
            "threshold_failures": failures,
            "sample_size": results.get("sample_size", 0),
        }

    def backtest_multiple_variants(
        self,
        commodity: str,
        current_prices: list[float],
        current_volumes: list[int],
        strategies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Backtest multiple strategy variants.

        Args:
            commodity: Commodity symbol
            current_prices: Current price series
            current_volumes: Current volume series
            strategies: List of strategy definitions

        Returns:
            List of backtest results for each strategy
        """
        results = []
        for strategy in strategies:
            result = self.backtest_strategy(
                commodity, current_prices, current_volumes, strategy
            )
            result["strategy_id"] = strategy.get("id", "unknown")
            result["variant"] = strategy.get("variant", "unknown")
            results.append(result)

        return results

    def get_confidence_score(self, backtest_results: dict[str, Any]) -> float:
        """Calculate confidence score from backtest results.

        Args:
            backtest_results: Backtest results dictionary

        Returns:
            Confidence score between 0 and 1
        """
        if not backtest_results.get("valid", False):
            return 0.0

        metrics = backtest_results.get("metrics", {})

        # Weight factors
        weights = {
            "win_rate": 0.25,
            "sharpe_ratio": 0.25,
            "expectancy": 0.20,
            "sample_size": 0.15,
            "pattern_similarity": 0.15,
        }

        scores = {}

        # Win rate score (0-1, optimal at 60-70%)
        win_rate = metrics.get("win_rate", 0)
        scores["win_rate"] = min(win_rate / 0.65, 1.0) if win_rate > 0 else 0

        # Sharpe ratio score (0-1, optimal > 1.5)
        sharpe = metrics.get("sharpe_ratio", 0)
        scores["sharpe_ratio"] = min(sharpe / 1.5, 1.0) if sharpe > 0 else 0

        # Expectancy score (normalized)
        expectancy = metrics.get("expectancy", 0)
        scores["expectancy"] = min(expectancy / 5, 1.0) if expectancy > 0 else 0

        # Sample size score (more is better, optimal at 50+)
        sample_size = metrics.get("sample_size", 0)
        scores["sample_size"] = min(sample_size / 50, 1.0)

        # Pattern similarity score
        similarity = metrics.get("avg_pattern_similarity", 0)
        scores["pattern_similarity"] = similarity

        # Calculate weighted score
        confidence = sum(
            scores.get(factor, 0) * weight
            for factor, weight in weights.items()
        )

        return min(max(confidence, 0.0), 1.0)

    def compare_strategies(
        self, backtest_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Compare multiple strategies and rank them.

        Args:
            backtest_results: List of backtest results

        Returns:
            Comparison results with rankings
        """
        # Filter valid results
        valid_results = [r for r in backtest_results if r.get("valid", False)]

        if not valid_results:
            return {
                "ranked_strategies": [],
                "best_strategy": None,
                "recommendation": "No valid strategies found",
            }

        # Add confidence scores
        for result in valid_results:
            result["confidence_score"] = self.get_confidence_score(result)

        # Rank by confidence score
        ranked = sorted(
            valid_results,
            key=lambda x: x.get("confidence_score", 0),
            reverse=True,
        )

        # Get best strategy
        best = ranked[0] if ranked else None

        return {
            "ranked_strategies": ranked,
            "best_strategy": best,
            "recommendation": best.get("variant", "unknown") if best else None,
        }

    def run_monte_carlo(
        self,
        commodity: str,
        current_prices: list[float],
        current_volumes: list[int],
        strategy: dict[str, Any],
        simulations: int = 1000,
    ) -> dict[str, Any]:
        """Run Monte Carlo simulation.

        Args:
            commodity: Commodity symbol
            current_prices: Current price series
            current_volumes: Current volume series
            strategy: Strategy definition
            simulations: Number of Monte Carlo simulations

        Returns:
            Monte Carlo results
        """
        import numpy as np

        # Get base backtest results
        base_results = self.backtest_strategy(
            commodity, current_prices, current_volumes, strategy
        )

        if not base_results.get("valid", False):
            return {"valid": False, "error": "Base backtest failed"}

        metrics = base_results.get("metrics", {})
        avg_return = metrics.get("avg_return", 0)
        std_dev = metrics.get("std_dev", 1)

        # Run Monte Carlo simulations
        mc_returns = []
        for _ in range(simulations):
            # Random return based on historical distribution
            random_return = np.random.normal(avg_return, std_dev)
            mc_returns.append(random_return)

        # Calculate percentiles
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        mc_percentiles = {
            f"p{p}": np.percentile(mc_returns, p) for p in percentiles
        }

        # Probability of profit
        prob_profit = sum(1 for r in mc_returns if r > 0) / len(mc_returns)

        return {
            "valid": True,
            "simulations": simulations,
            "probability_of_profit": prob_profit,
            "percentiles": mc_percentiles,
            "worst_case": mc_percentiles["p5"],
            "best_case": mc_percentiles["p95"],
            "expected_return": np.mean(mc_returns),
            "base_metrics": metrics,
        }
