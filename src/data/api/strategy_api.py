"""Strategy API for validated trading strategies."""

from datetime import datetime
from typing import Any

from src.emergency.detector import EmergencyDetector
from src.emergency.responder import EmergencyResponder

# Singleton instances
_strategy_generator = None
_emergency_detector: EmergencyDetector | None = None
_emergency_responder: EmergencyResponder | None = None


def _get_strategy_generator():
    """Get or create strategy generator singleton."""
    global _strategy_generator
    if _strategy_generator is None:
        from src.strategy.generator import StrategyGenerator
        _strategy_generator = StrategyGenerator()
    return _strategy_generator


def _get_emergency_detector() -> EmergencyDetector:
    """Get or create emergency detector singleton."""
    global _emergency_detector
    if _emergency_detector is None:
        _emergency_detector = EmergencyDetector()
    return _emergency_detector


def _get_emergency_responder() -> EmergencyResponder:
    """Get or create emergency responder singleton."""
    global _emergency_responder
    if _emergency_responder is None:
        _emergency_responder = EmergencyResponder()
    return _emergency_responder


def get_validated_insight(commodity: str) -> dict[str, Any]:
    """Get validated trading strategies for a commodity.

    This is the main API for getting AI-generated strategies that have
    passed historical backtesting. Returns multiple variants (conservative,
    balanced, aggressive) with confidence scores.

    Args:
        commodity: Commodity symbol (GOLD, OIL)

    Returns:
        Validated insight with strategies

    Example:
        >>> result = get_validated_insight("GOLD")
        >>> print(f"Best strategy: {result['best_strategy']['variant']}")
        >>> print(f"Confidence: {result['best_strategy']['confidence_score']:.0%}")
    """
    generator = _get_strategy_generator()

    # Generate strategies
    result = generator.generate_strategies(commodity, use_rl=True)

    # Format for API
    return {
        "commodity": result["commodity"],
        "current_price": result["current_price"],
        "current_context": result["current_context"],
        "strategies": [
            {
                "id": s.get("prediction_id", ""),
                "variant": s["strategy"].variant,
                "recommendation": s["strategy"].recommendation,
                "entry_price": s["strategy"].entry_price,
                "target_price": s["strategy"].target_price,
                "stop_loss": s["strategy"].stop_loss,
                "position_size": s["strategy"].position_size,
                "reasoning": s["strategy"].reasoning,
                "key_factors": s["strategy"].key_factors,
                "risk_level": s["strategy"].risk_level,
                "backtest_results": s.get("backtest", {}),
                "confidence_score": s.get("confidence_score", 0),
                "status": s.get("status", "rejected"),
            }
            for s in result["strategies"]
        ],
        "best_strategy": result.get("best_strategy"),
        "emergency_alert": None,  # Will be d separately
        "generated_at": datetime.utcnow().isoformat(),
    }


def get_strategy_backtest(strategy_id: str) -> dict[str, Any]:
    """Get detailed backtest results for a strategy.

    Args:
        strategy_id: Strategy prediction ID

    Returns:
        Detailed backtest results
    """
    # This would query the prediction tracker for detailed results
    return {
        "strategy_id": strategy_id,
        "message": "Use prediction_tracker for detailed results",
    }


def get_emergency_status(commodity: str | None = None) -> dict[str, Any]:
    """Get current emergency status.

    Args:
        commodity: Optional commodity filter

    Returns:
        Emergency status
    """
    detector = _get_emergency_detector()
    responder = _get_emergency_responder()

    if commodity:
        # Check specific commodity
        alerts = detector.detect_all(commodity)
        summary = detector.get_emergency_summary(alerts)

        if summary["has_emergency"]:
            response = responder.respond(alerts[0])
            return {
                "has_emergency": True,
                "commodity": commodity,
                "summary": summary,
                "response": response,
            }

        return {
            "has_emergency": False,
            "commodity": commodity,
        }
    else:
        # Check all commodities
        all_alerts = []
        for comm in ["GOLD", "OIL"]:
            alerts = detector.detect_all(comm)
            all_alerts.extend(alerts)

        summary = detector.get_emergency_summary(all_alerts)

        if summary["has_emergency"]:
            response = responder.respond_multiple(all_alerts)
            return {
                "has_emergency": True,
                "summary": summary,
                "response": response,
            }

        return {
            "has_emergency": False,
            "monitored_commodities": ["GOLD", "OIL"],
        }


def get_learning_stats(commodity: str | None = None) -> dict[str, Any]:
    """Get reinforcement learning statistics.

    Args:
        commodity: Optional commodity filter

    Returns:
        RL learning statistics
    """
    from src.data.ingestion.prediction_tracker import PredictionTracker

    tracker = PredictionTracker()
    return tracker.get_learning_stats(commodity)


def get_pattern_analysis(commodity: str) -> dict[str, Any]:
    """Get pattern analysis for a commodity.

    Args:
        commodity: Commodity symbol

    Returns:
        Pattern analysis
    """
    from src.backtest.simulator import PatternSimulator

    simulator = PatternSimulator()
    return simulator.get_pattern_distribution(commodity)


# Export all functions
__all__ = [
    "get_validated_insight",
    "get_strategy_backtest",
    "get_emergency_status",
    "get_learning_stats",
    "get_pattern_analysis",
]
