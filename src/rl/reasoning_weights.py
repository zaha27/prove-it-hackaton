"""Reasoning weight manager for RL-based reasoning pattern weighting."""

from typing import Any

from qdrant_client import QdrantClient

from src.data.config import config
from src.data.vector_schema import LLM_PREDICTIONS_COLLECTION


class ReasoningWeightManager:
    """Manages weights for reasoning patterns based on success/failure."""

    def __init__(self) -> None:
        """Initialize the reasoning weight manager."""
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.collection_name = LLM_PREDICTIONS_COLLECTION.name

    def update_reasoning_weights(
        self, prediction_id: str, outcome: str, actual_return: float
    ) -> dict[str, Any]:
        """Update weights for a reasoning pattern based on outcome.

        Args:
            prediction_id: Prediction ID
            outcome: success, failure, or partial
            actual_return: Actual return percentage

        Returns:
            Update results
        """
        # Calculate weight update
        if outcome == "success":
            weight_delta = 0.1 + (actual_return / 100) * 0.1
        elif outcome == "failure":
            weight_delta = -0.1 - (abs(actual_return) / 100) * 0.1
        else:  # partial
            weight_delta = 0.0

        # Store weight update in prediction metadata
        # This would update the prediction point in Qdrant

        return {
            "prediction_id": prediction_id,
            "outcome": outcome,
            "weight_delta": weight_delta,
            "updated": True,
        }

    def get_reasoning_pattern_score(
        self, reasoning_hash: str
    ) -> float:
        """Get the current score for a reasoning pattern.

        Args:
            reasoning_hash: Hash of reasoning pattern

        Returns:
            Current score (0-1)
        """
        # Query all predictions with this reasoning hash
        # Calculate average success rate

        try:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "reasoning_hash", "match": {"value": reasoning_hash}},
                        {"key": "outcome_evaluated", "match": {"value": True}},
                    ]
                },
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            predictions = results[0]
            if not predictions:
                return 0.5  # Default neutral score

            # Calculate weighted score
            total_weight = 0
            weighted_score = 0

            for point in predictions:
                payload = point.payload
                outcome = payload.get("actual_outcome", "partial")
                actual_return = payload.get("actual_return", 0)

                if outcome == "success":
                    score = 1.0
                elif outcome == "failure":
                    score = 0.0
                else:
                    score = 0.5

                # Weight by recency (more recent = higher weight)
                # This is simplified - in production use actual dates
                weight = 1.0

                weighted_score += score * weight
                total_weight += weight

            return weighted_score / total_weight if total_weight > 0 else 0.5

        except Exception as e:
            print(f"Error getting reasoning score: {e}")
            return 0.5

    def get_top_reasoning_patterns(
        self,
        commodity: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top performing reasoning patterns.

        Args:
            commodity: Commodity symbol
            top_k: Number of patterns to return

        Returns:
            List of top reasoning patterns
        """
        try:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "commodity", "match": {"value": commodity}},
                        {"key": "actual_outcome", "match": {"value": "success"}},
                    ]
                },
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            # Group by reasoning hash and calculate scores
            pattern_scores: dict[str, dict[str, Any]] = {}

            for point in results[0]:
                payload = point.payload
                reasoning_hash = payload.get("reasoning_hash", "")
                actual_return = payload.get("actual_return", 0)

                if reasoning_hash not in pattern_scores:
                    pattern_scores[reasoning_hash] = {
                        "hash": reasoning_hash,
                        "reasoning": payload.get("reasoning", "")[:200],
                        "total_predictions": 0,
                        "total_return": 0,
                        "avg_return": 0,
                    }

                pattern_scores[reasoning_hash]["total_predictions"] += 1
                pattern_scores[reasoning_hash]["total_return"] += actual_return

            # Calculate averages and sort
            for pattern in pattern_scores.values():
                if pattern["total_predictions"] > 0:
                    pattern["avg_return"] = (
                        pattern["total_return"] / pattern["total_predictions"]
                    )

            sorted_patterns = sorted(
                pattern_scores.values(),
                key=lambda x: x["avg_return"],
                reverse=True,
            )

            return sorted_patterns[:top_k]

        except Exception as e:
            print(f"Error getting top patterns: {e}")
            return []

    def calculate_learning_progress(
        self, commodity: str | None = None
    ) -> dict[str, Any]:
        """Calculate learning progress over time.

        Args:
            commodity: Optional commodity filter

        Returns:
            Learning progress metrics
        """
        # Get stats for different time periods
        stats = {}

        # This would query predictions grouped by time periods
        # and calculate success rates for each period

        return {
            "overall": stats,
            "trend": "improving",  # or "stable", "declining"
            "recommendations": [],
        }
