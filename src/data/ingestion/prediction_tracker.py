"""Prediction tracker for reinforcement learning.

This module tracks all LLM predictions and their outcomes to enable
reinforcement learning from past successes and failures.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from src.data.config import config
from src.data.vector_schema import LLM_PREDICTIONS_COLLECTION


class PredictionTracker:
    """Tracks LLM predictions for reinforcement learning."""

    def __init__(self) -> None:
        """Initialize the prediction tracker."""
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.collection_name = LLM_PREDICTIONS_COLLECTION.name

        # RL parameters from config
        self.evaluation_days = int(
            getattr(config, "rl_outcome_evaluation_days", 7)
        )
        self.success_threshold = float(
            getattr(config, "rl_success_threshold", 0.02)
        )
        self.failure_threshold = float(
            getattr(config, "rl_failure_threshold", -0.02)
        )

    def _generate_prediction_id(
        self, commodity: str, timestamp: datetime
    ) -> str:
        """Generate unique ID for a prediction.

        Args:
            commodity: Commodity symbol
            timestamp: Prediction timestamp

        Returns:
            Unique prediction ID
        """
        content = f"{commodity}:{timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _embed_reasoning(self, reasoning: str) -> list[float]:
        """Create embedding from reasoning text.

        Args:
            reasoning: Reasoning text

        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(
            reasoning, convert_to_tensor=False
        )
        return embedding.tolist()

    def track_prediction(
        self,
        commodity: str,
        recommendation: str,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        reasoning: str,
        strategy_variant: str = "balanced",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Track a new LLM prediction.

        Args:
            commodity: Commodity symbol
            recommendation: BUY, SELL, or HOLD
            entry_price: Entry price
            target_price: Target price
            stop_loss: Stop loss price
            reasoning: LLM reasoning text
            strategy_variant: conservative, balanced, or aggressive
            metadata: Additional metadata

        Returns:
            Prediction ID
        """
        prediction_id = self._generate_prediction_id(
            commodity, datetime.utcnow()
        )

        # Embed reasoning for similarity search
        reasoning_embedding = self._embed_reasoning(reasoning)
        reasoning_hash = hashlib.md5(reasoning.encode()).hexdigest()[:12]

        payload = {
            "prediction_id": prediction_id,
            "commodity": commodity,
            "prediction_date": datetime.utcnow().isoformat(),
            "evaluation_date": (
                datetime.utcnow() + timedelta(days=self.evaluation_days)
            ).isoformat(),
            "recommendation": recommendation,
            "entry_price": entry_price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "reasoning": reasoning,
            "reasoning_hash": reasoning_hash,
            "strategy_variant": strategy_variant,
            "outcome_evaluated": False,
            "actual_outcome": "pending",
            "actual_return": 0.0,
            "hit_target": False,
            "hit_stop_loss": False,
            "time_to_target_days": -1,
            "confidence_score": metadata.get("confidence_score", 0.5) if metadata else 0.5,
            "backtest_win_rate": metadata.get("win_rate", 0.0) if metadata else 0.0,
            "backtest_sharpe": metadata.get("sharpe", 0.0) if metadata else 0.0,
            "metadata": metadata or {},
        }

        point = PointStruct(
            id=prediction_id,
            vector=reasoning_embedding,
            payload=payload,
        )

        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return prediction_id

    def evaluate_prediction(
        self,
        prediction_id: str,
        actual_prices: list[float],
        price_dates: list[str],
    ) -> dict[str, Any]:
        """Evaluate a prediction against actual price data.

        Args:
            prediction_id: Prediction ID
            actual_prices: List of actual prices after prediction
            price_dates: Corresponding dates

        Returns:
            Evaluation results
        """
        # Fetch prediction
        result = self.qdrant.retrieve(
            collection_name=self.collection_name,
            ids=[prediction_id],
            with_payload=True,
        )

        if not result:
            raise ValueError(f"Prediction {prediction_id} not found")

        prediction = result[0].payload

        entry_price = prediction["entry_price"]
        target_price = prediction["target_price"]
        stop_loss = prediction["stop_loss"]
        recommendation = prediction["recommendation"]

        # Simulate the trade
        hit_target = False
        hit_stop = False
        exit_price = actual_prices[-1] if actual_prices else entry_price
        exit_day = len(actual_prices)

        for i, price in enumerate(actual_prices):
            if recommendation.upper() == "BUY":
                if price >= target_price:
                    hit_target = True
                    exit_price = target_price
                    exit_day = i + 1
                    break
                elif price <= stop_loss:
                    hit_stop = True
                    exit_price = stop_loss
                    exit_day = i + 1
                    break
            elif recommendation.upper() == "SELL":
                if price <= target_price:
                    hit_target = True
                    exit_price = target_price
                    exit_day = i + 1
                    break
                elif price >= stop_loss:
                    hit_stop = True
                    exit_price = stop_loss
                    exit_day = i + 1
                    break

        # Calculate return
        if recommendation.upper() == "BUY":
            actual_return = (exit_price / entry_price - 1) * 100
        else:  # SELL
            actual_return = (entry_price / exit_price - 1) * 100

        # Determine outcome
        if hit_target:
            outcome = "success"
        elif hit_stop:
            outcome = "failure"
        elif actual_return >= self.success_threshold * 100:
            outcome = "success"
        elif actual_return <= self.failure_threshold * 100:
            outcome = "failure"
        else:
            outcome = "partial"

        # Update prediction in DB
        update_payload = {
            "outcome_evaluated": True,
            "actual_outcome": outcome,
            "actual_return": actual_return,
            "hit_target": hit_target,
            "hit_stop_loss": hit_stop,
            "time_to_target_days": exit_day if hit_target else -1,
            "exit_price": exit_price,
            "evaluation_timestamp": datetime.utcnow().isoformat(),
        }

        # Get existing payload and merge
        existing_payload = dict(prediction)
        existing_payload.update(update_payload)

        # Re-upsert with updated payload
        point = PointStruct(
            id=prediction_id,
            vector=result[0].vector if result[0].vector else [],
            payload=existing_payload,
        )

        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return {
            "prediction_id": prediction_id,
            "outcome": outcome,
            "actual_return": actual_return,
            "hit_target": hit_target,
            "hit_stop_loss": hit_stop,
            "exit_day": exit_day,
        }

    def get_successful_reasoning_patterns(
        self,
        commodity: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Get successful reasoning patterns for RAG.

        Args:
            commodity: Commodity symbol
            top_k: Number of patterns to retrieve

        Returns:
            List of successful prediction patterns
        """
        try:
            # Scroll through predictions and filter for successes
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "commodity", "match": {"value": commodity}},
                        {"key": "actual_outcome", "match": {"value": "success"}},
                        {"key": "outcome_evaluated", "match": {"value": True}},
                    ]
                },
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            patterns = []
            for point in results[0]:
                payload = point.payload
                patterns.append({
                    "reasoning": payload.get("reasoning", ""),
                    "actual_return": payload.get("actual_return", 0),
                    "strategy_variant": payload.get("strategy_variant", "balanced"),
                    "prediction_date": payload.get("prediction_date", ""),
                })

            # Sort by return and take top_k
            patterns.sort(key=lambda x: x["actual_return"], reverse=True)
            return patterns[:top_k]

        except Exception as e:
            print(f"Error retrieving successful patterns: {e}")
            return []

    def get_learning_stats(self, commodity: str | None = None) -> dict[str, Any]:
        """Get reinforcement learning statistics.

        Args:
            commodity: Optional commodity filter

        Returns:
            Dictionary with learning statistics
        """
        try:
            filter_conditions = [{"key": "outcome_evaluated", "match": {"value": True}}]
            if commodity:
                filter_conditions.append(
                    {"key": "commodity", "match": {"value": commodity}}
                )

            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={"must": filter_conditions},
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            predictions = [p.payload for p in results[0]]

            if not predictions:
                return {"total_evaluated": 0}

            outcomes = [p["actual_outcome"] for p in predictions]
            returns = [p["actual_return"] for p in predictions]

            success_count = outcomes.count("success")
            failure_count = outcomes.count("failure")
            partial_count = outcomes.count("partial")
            total = len(outcomes)

            return {
                "total_evaluated": total,
                "success_count": success_count,
                "failure_count": failure_count,
                "partial_count": partial_count,
                "success_rate": success_count / total if total > 0 else 0,
                "avg_return": sum(returns) / len(returns) if returns else 0,
                "best_return": max(returns) if returns else 0,
                "worst_return": min(returns) if returns else 0,
            }

        except Exception as e:
            print(f"Error getting learning stats: {e}")
            return {"error": str(e)}

    def find_similar_successful_predictions(
        self,
        current_reasoning: str,
        commodity: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find similar successful predictions for weighted RAG.

        Args:
            current_reasoning: Current reasoning text to compare
            commodity: Commodity symbol
            top_k: Number of similar predictions

        Returns:
            List of similar successful predictions
        """
        # Embed current reasoning
        query_embedding = self._embed_reasoning(current_reasoning)

        # Search for similar predictions
        from qdrant_client.models import SearchParams
        results = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k * 3,  # Get more to filter
            query_filter={
                "must": [
                    {"key": "commodity", "match": {"value": commodity}},
                    {"key": "actual_outcome", "match": {"value": "success"}},
                ]
            },
        ).points

        similar = []
        for result in results[:top_k]:
            payload = result.payload
            # Weight by similarity * success score
            weight = result.score * (1 + payload.get("actual_return", 0) / 100)
            similar.append({
                "reasoning": payload.get("reasoning", ""),
                "actual_return": payload.get("actual_return", 0),
                "weight": weight,
                "similarity": result.score,
            })

        return similar
