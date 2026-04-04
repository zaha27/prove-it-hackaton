"""Strategy validator with threshold checking."""

from typing import Any

from src.backtest.engine import BacktestEngine
from src.backtest.metrics import passes_thresholds
from src.data.config import config


class StrategyValidator:
    """Validates strategies against backtest thresholds."""

    def __init__(self) -> None:
        """Initialize the strategy validator."""
        self.backtest_engine = BacktestEngine()
        self.config = config

    def validate_strategy(
        self,
        strategy: dict[str, Any],
        backtest_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a strategy against all criteria.

        Args:
            strategy: Strategy definition
            backtest_results: Backtest results

        Returns:
            Validation results
        """
        validation = {
            "valid": False,
            "status": "rejected",
            "checks": {},
            "failures": [],
        }

        # Check if backtest was valid
        if not backtest_results.get("valid", False):
            validation["checks"]["backtest_valid"] = False
            validation["failures"].append("Backtest failed")
            return validation

        validation["checks"]["backtest_valid"] = True

        # Get metrics
        metrics = backtest_results.get("metrics", {})

        # Check sample size
        sample_size = metrics.get("sample_size", 0)
        if sample_size < self.config.backtest_min_sample_size:
            validation["checks"]["sample_size"] = False
            validation["failures"].append(
                f"Sample size {sample_size} < {self.config.backtest_min_sample_size}"
            )
        else:
            validation["checks"]["sample_size"] = True

        # Check thresholds
        passes, failures = passes_thresholds(metrics, self.config)
        validation["checks"]["thresholds"] = passes
        validation["failures"].extend(failures)

        # Check confidence score
        confidence = self.backtest_engine.get_confidence_score(backtest_results)
        if confidence < 0.5:
            validation["checks"]["confidence"] = False
            validation["failures"].append(
                f"Confidence {confidence:.2f} below 0.5 threshold"
            )
        else:
            validation["checks"]["confidence"] = True

        # Determine overall validity
        validation["valid"] = all(validation["checks"].values())
        validation["status"] = "validated" if validation["valid"] else "rejected"
        validation["confidence_score"] = confidence

        return validation

    def validate_multiple(
        self,
        strategies_with_backtests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Validate multiple strategies.

        Args:
            strategies_with_backtests: List of strategy/backtest pairs

        Returns:
            List of validation results
        """
        results = []
        for item in strategies_with_backtests:
            strategy = item.get("strategy", {})
            backtest = item.get("backtest", {})

            validation = self.validate_strategy(strategy, backtest)
            results.append({
                "strategy": strategy,
                "backtest": backtest,
                "validation": validation,
            })

        return results

    def get_validation_summary(
        self, validations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Get summary of validations.

        Args:
            validations: List of validation results

        Returns:
            Summary statistics
        """
        total = len(validations)
        validated = sum(1 for v in validations if v["validation"]["valid"])
        rejected = total - validated

        # Get average confidence scores
        confidence_scores = [
            v["validation"].get("confidence_score", 0)
            for v in validations
        ]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        # Get best strategy
        best = None
        best_confidence = 0
        for v in validations:
            if v["validation"]["valid"]:
                conf = v["validation"].get("confidence_score", 0)
                if conf > best_confidence:
                    best_confidence = conf
                    best = v

        return {
            "total_strategies": total,
            "validated": validated,
            "rejected": rejected,
            "validation_rate": validated / total if total > 0 else 0,
            "average_confidence": avg_confidence,
            "best_strategy": best,
        }
