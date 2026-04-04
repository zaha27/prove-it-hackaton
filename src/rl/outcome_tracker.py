"""Outcome tracker for evaluating prediction performance."""

from datetime import datetime, timedelta
from typing import Any

from src.data.clients.yfinance_client import YFinanceClient
from src.data.config import config
from src.data.ingestion.prediction_tracker import PredictionTracker


class OutcomeTracker:
    """Tracks and evaluates prediction outcomes."""

    def __init__(self) -> None:
        """Initialize the outcome tracker."""
        self.prediction_tracker = PredictionTracker()
        self.price_client = YFinanceClient()
        self.evaluation_days = config.rl_outcome_evaluation_days

    def evaluate_pending_predictions(self) -> list[dict[str, Any]]:
        """Evaluate all pending predictions that are due.

        Returns:
            List of evaluation results
        """
        # Get predictions that need evaluation
        # This would query the vector DB for predictions where
        # evaluation_date <= now and outcome_evaluated = False

        # For now, return empty list (implementation depends on vector query)
        return []

    def evaluate_prediction(
        self,
        prediction_id: str,
        actual_prices: list[float] | None = None,
    ) -> dict[str, Any]:
        """Evaluate a specific prediction.

        Args:
            prediction_id: Prediction ID
            actual_prices: Optional actual prices (fetched if not provided)

        Returns:
            Evaluation results
        """
        # If prices not provided, fetch them
        if actual_prices is None:
            actual_prices = self._fetch_prices_for_prediction(prediction_id)

        if not actual_prices:
            return {
                "prediction_id": prediction_id,
                "evaluated": False,
                "error": "Could not fetch prices",
            }

        # Run evaluation
        result = self.prediction_tracker.evaluate_prediction(
            prediction_id=prediction_id,
            actual_prices=actual_prices,
            price_dates=[],  # Not needed for evaluation
        )

        return result

    def _fetch_prices_for_prediction(self, prediction_id: str) -> list[float]:
        """Fetch prices for a prediction evaluation.

        Args:
            prediction_id: Prediction ID

        Returns:
            List of prices
        """
        # This would fetch from the prediction tracker and then
        # get historical prices from yfinance
        # Implementation depends on how we store prediction dates
        return []

    def batch_evaluate(
        self, prediction_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Evaluate multiple predictions.

        Args:
            prediction_ids: List of prediction IDs

        Returns:
            List of evaluation results
        """
        results = []
        for pred_id in prediction_ids:
            result = self.evaluate_prediction(pred_id)
            results.append(result)
        return results

    def get_performance_summary(
        self, commodity: str | None = None, days: int = 30
    ) -> dict[str, Any]:
        """Get performance summary for RL learning.

        Args:
            commodity: Optional commodity filter
            days: Days to look back

        Returns:
            Performance summary
        """
        return self.prediction_tracker.get_learning_stats(commodity)

    def calculate_success_metrics(
        self, evaluations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate success metrics from evaluations.

        Args:
            evaluations: List of evaluation results

        Returns:
            Success metrics
        """
        if not evaluations:
            return {"total": 0, "success_rate": 0}

        total = len(evaluations)
        successes = sum(1 for e in evaluations if e.get("outcome") == "success")
        failures = sum(1 for e in evaluations if e.get("outcome") == "failure")
        partials = sum(1 for e in evaluations if e.get("outcome") == "partial")

        returns = [e.get("actual_return", 0) for e in evaluations]

        return {
            "total": total,
            "successes": successes,
            "failures": failures,
            "partials": partials,
            "success_rate": successes / total if total > 0 else 0,
            "avg_return": sum(returns) / len(returns) if returns else 0,
            "best_return": max(returns) if returns else 0,
            "worst_return": min(returns) if returns else 0,
        }
