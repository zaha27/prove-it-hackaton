"""Deep research agent using Gemma4 for autonomous analysis."""

import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.data.config import config
from src.data.vector_schema import LLM_PREDICTIONS_COLLECTION
from src.rl.ollama_client import OllamaClient


class DeepResearcher:
    """Autonomous research agent using Gemma4 for deep analysis."""

    def __init__(self) -> None:
        """Initialize the deep researcher."""
        self.ollama = OllamaClient()
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.collection_name = LLM_PREDICTIONS_COLLECTION.name
        self.research_dir = tempfile.mkdtemp(prefix="research_")

    def research_failed_predictions(
        self, min_confidence: float = 0.3
    ) -> dict[str, Any]:
        """Analyze failed predictions and generate hypotheses.

        Args:
            min_confidence: Minimum confidence to consider "failed"

        Returns:
            Research findings
        """
        print("🔍 Researching failed predictions...")

        # Query failed predictions from Qdrant
        failed = self._query_failed_predictions(min_confidence)

        if not failed:
            return {"status": "no_data", "message": "No failed predictions found"}

        print(f"  Found {len(failed)} failed predictions to analyze")

        # Send to Gemma4 for analysis
        analysis = self.ollama.analyze_patterns(
            patterns=failed,
            question="What common patterns exist in these failed predictions? "
            "What factors might have caused the failures?",
        )

        # Generate hypotheses
        hypotheses = []
        for failure in failed[:5]:  # Top 5 failures
            hypothesis = self.ollama.generate_hypothesis(
                {
                    "prediction": failure.get("reasoning", "")[:500],
                    "expected": failure.get("predicted_direction", "unknown"),
                    "actual": failure.get("actual_return", 0),
                    "confidence": failure.get("confidence", 0),
                }
            )
            hypotheses.append(hypothesis)

        # Write script to test hypotheses
        script = self.ollama.write_analysis_script(
            task_description="Analyze failed predictions to identify common failure modes. "
            "Calculate correlation between prediction confidence and actual accuracy. "
            "Identify which features are most predictive of failure.",
            data_schema={
                "predictions": [
                    {
                        "reasoning": "string",
                        "predicted_direction": "string",
                        "actual_return": "float",
                        "confidence": "float",
                        "commodity": "string",
                        "timestamp": "string",
                    }
                ]
            },
        )

        # Execute script
        script_path = os.path.join(self.research_dir, "analyze_failures.py")
        with open(script_path, "w") as f:
            f.write(script)

        result = self._execute_script(script_path, {"predictions": failed})

        # Store findings
        findings = {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis,
            "hypotheses": hypotheses,
            "script_result": result,
            "prediction_count": len(failed),
        }

        self._store_findings("failed_prediction_analysis", findings)

        return findings

    def find_hidden_patterns(self, commodity: str = "GOLD") -> dict[str, Any]:
        """Find non-obvious patterns in price data.

        Args:
            commodity: Commodity to analyze

        Returns:
            Discovered patterns
        """
        print(f"🔍 Mining hidden patterns for {commodity}...")

        # Query price patterns
        patterns = self._query_price_patterns(commodity)

        if not patterns:
            return {"status": "no_data", "message": f"No patterns found for {commodity}"}

        print(f"  Analyzing {len(patterns)} patterns...")

        # Ask Gemma4 to find correlations
        analysis = self.ollama.analyze_patterns(
            patterns=patterns,
            question="Find non-obvious correlations in this price data. "
            "Consider: time of day effects, day of week patterns, "
            "volatility clustering, volume-price relationships, "
            "and any other hidden features that might predict returns.",
        )

        # Generate script to validate findings
        script = self.ollama.write_analysis_script(
            task_description=f"Validate pattern hypotheses for {commodity}. "
            "Calculate feature importance using XGBoost. "
            "Identify which engineered features have predictive power.",
            data_schema={
                "patterns": [
                    {
                        "prices": "list[float]",
                        "volumes": "list[float]",
                        "date": "string",
                        "next_7d_return": "float",
                        "next_30d_return": "float",
                        "volatility_regime": "string",
                    }
                ]
            },
        )

        script_path = os.path.join(self.research_dir, f"validate_patterns_{commodity}.py")
        with open(script_path, "w") as f:
            f.write(script)

        result = self._execute_script(script_path, {"patterns": patterns})

        findings = {
            "timestamp": datetime.utcnow().isoformat(),
            "commodity": commodity,
            "analysis": analysis,
            "script_result": result,
            "pattern_count": len(patterns),
        }

        self._store_findings(f"hidden_patterns_{commodity}", findings)

        return findings

    def deep_reasoning_on_prediction(
        self, prediction: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform deep reasoning on a low-confidence prediction.

        Only called when primary model has low confidence.

        Args:
            prediction: Prediction to reason about

        Returns:
            Deep reasoning result
        """
        confidence = prediction.get("confidence", 0)

        # Only use Gemma4 for low-confidence scenarios
        if confidence >= 0.7:
            return {
                "status": "skipped",
                "reason": "Confidence too high for deep reasoning",
                "confidence": confidence,
            }

        print(f"🧠 Deep reasoning on low-confidence prediction ({confidence:.2f})...")

        # Get context
        context = self._build_context(prediction)

        # Perform deep reasoning
        result = self.ollama.deep_reasoning(
            context=context,
            question=f"Should we trust this prediction? {prediction.get('reasoning', '')}",
            confidence_threshold=0.6,
        )

        # If still uncertain, generate research task
        if result.get("needs_more_research"):
            research_task = self._generate_research_task(prediction, result)
            result["research_task"] = research_task

        # Store reasoning
        self._store_findings("deep_reasoning", {
            "timestamp": datetime.utcnow().isoformat(),
            "prediction": prediction,
            "reasoning": result,
        })

        return result

    def continuous_learning_loop(self, interval_minutes: int = 60) -> None:
        """Run continuous learning cycle.

        Args:
            interval_minutes: Minutes between research cycles
        """
        print("🔄 Starting continuous learning loop...")
        print(f"  Interval: {interval_minutes} minutes")
        print("  Press Ctrl+C to stop")

        try:
            while True:
                cycle_start = time.time()

                # Research failed predictions
                self.research_failed_predictions()

                # Find patterns for each commodity
                for commodity in ["GOLD", "OIL"]:
                    self.find_hidden_patterns(commodity)

                # Sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, interval_minutes * 60 - elapsed)

                if sleep_time > 0:
                    print(f"⏳ Sleeping for {sleep_time/60:.1f} minutes...")
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n🛑 Learning loop stopped")

    def get_latest_findings(self, category: str | None = None) -> list[dict[str, Any]]:
        """Get latest research findings.

        Args:
            category: Optional category filter

        Returns:
            List of findings
        """
        filter_dict = {}
        if category:
            filter_dict = {"must": [{"key": "category", "match": {"value": category}}]}

        results = self.qdrant.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_dict if filter_dict else None,
            limit=100,
            with_payload=True,
        )

        return [point.payload for point in results[0] if point.payload]

    def _query_failed_predictions(
        self, min_confidence: float
    ) -> list[dict[str, Any]]:
        """Query failed predictions from Qdrant."""
        try:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "confidence", "range": {"lt": min_confidence}},
                        {"key": "evaluated", "match": {"value": True}},
                    ]
                },
                limit=100,
                with_payload=True,
            )

            return [
                {
                    **point.payload,
                    "id": point.id,
                }
                for point in results[0]
                if point.payload
            ]
        except Exception as e:
            print(f"Error querying failed predictions: {e}")
            return []

    def _query_price_patterns(self, commodity: str) -> list[dict[str, Any]]:
        """Query price patterns from Qdrant."""
        from src.data.vector_schema import PRICE_PATTERNS_COLLECTION

        try:
            results = self.qdrant.scroll(
                collection_name=PRICE_PATTERNS_COLLECTION.name,
                scroll_filter={
                    "must": [{"key": "commodity", "match": {"value": commodity}}]
                },
                limit=500,
                with_payload=True,
            )

            return [point.payload for point in results[0] if point.payload]
        except Exception as e:
            print(f"Error querying price patterns: {e}")
            return []

    def _execute_script(
        self, script_path: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a research script and capture results.

        Args:
            script_path: Path to Python script
            data: Input data for script

        Returns:
            Script execution results
        """
        # Write data to temp file
        data_path = script_path.replace(".py", "_input.json")
        with open(data_path, "w") as f:
            json.dump(data, f)

        # Execute script
        try:
            result = subprocess.run(
                ["python", script_path, data_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.research_dir,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Script timed out after 60s",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _build_context(self, prediction: dict[str, Any]) -> str:
        """Build context for deep reasoning."""
        commodity = prediction.get("commodity", "UNKNOWN")

        # Get similar historical predictions
        similar = self._query_similar_predictions(prediction)

        context_parts = [
            f"Commodity: {commodity}",
            f"Prediction: {prediction.get('reasoning', 'N/A')}",
            f"Confidence: {prediction.get('confidence', 0):.2f}",
            f"Predicted Direction: {prediction.get('predicted_direction', 'N/A')}",
            "",
            "Similar Historical Predictions:",
        ]

        for sim in similar[:5]:
            context_parts.append(
                f"- Return: {sim.get('actual_return', 0):+.1f}% | "
                f"Confidence: {sim.get('confidence', 0):.2f}"
            )

        return "\n".join(context_parts)

    def _query_similar_predictions(
        self, prediction: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Query similar historical predictions."""
        try:
            # This would use vector search in production
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "commodity",
                            "match": {"value": prediction.get("commodity", "")},
                        },
                        {"key": "evaluated", "match": {"value": True}},
                    ]
                },
                limit=20,
                with_payload=True,
            )

            return [point.payload for point in results[0] if point.payload]
        except Exception:
            return []

    def _generate_research_task(
        self, prediction: dict[str, Any], reasoning: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a research task for uncertain predictions."""
        return {
            "type": "investigate",
            "priority": "high",
            "description": f"Investigate low-confidence prediction for {prediction.get('commodity')}",
            "questions": reasoning.get("evidence", []),
            "created_at": datetime.utcnow().isoformat(),
        }

    def _store_findings(self, category: str, findings: dict[str, Any]) -> None:
        """Store research findings in Qdrant."""
        try:
            point_id = hashlib.md5(
                f"{category}:{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]

            point = PointStruct(
                id=point_id,
                vector=[0.0] * 384,  # Placeholder vector
                payload={
                    "category": category,
                    "findings": findings,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            print(f"  ✓ Stored findings: {category}")
        except Exception as e:
            print(f"  ✗ Failed to store findings: {e}")

    def check_health(self) -> dict[str, Any]:
        """Check health of all components."""
        ollama_health = self.ollama.check_health()

        try:
            collections = self.qdrant.get_collections()
            qdrant_health = {
                "status": "healthy",
                "collections": [c.name for c in collections.collections],
            }
        except Exception as e:
            qdrant_health = {"status": "error", "error": str(e)}

        return {
            "ollama": ollama_health,
            "qdrant": qdrant_health,
            "research_dir": self.research_dir,
        }
