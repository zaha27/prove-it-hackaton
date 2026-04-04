"""Pre-computed emergency strategies."""

from typing import Any


class EmergencyStrategies:
    """Repository of pre-computed emergency strategies."""

    def __init__(self) -> None:
        """Initialize emergency strategies."""
        self._strategies = self._load_strategies()

    def _load_strategies(self) -> dict[str, dict[str, Any]]:
        """Load pre-computed emergency strategies.

        Returns:
            Dictionary of strategies
        """
        return {
            "price_spike": {
                "critical": {
                    "risk_management": {
                        "max_position_size": "1% portfolio",
                        "max_risk_per_trade": "0.5% portfolio",
                        "use_guaranteed_stops": True,
                    },
                    "monitoring": [
                        "Check for news catalysts every 15 minutes",
                        "Monitor volume for confirmation",
                        "Watch for reversal patterns",
                        "Track correlated markets",
                    ],
                    "timeframe": "immediate",
                },
                "high": {
                    "risk_management": {
                        "max_position_size": "2% portfolio",
                        "max_risk_per_trade": "1% portfolio",
                        "use_trailing_stops": True,
                    },
                    "monitoring": [
                        "Check for news catalysts hourly",
                        "Monitor volume trends",
                        "Watch support/resistance levels",
                    ],
                    "timeframe": "within 1 hour",
                },
                "medium": {
                    "risk_management": {
                        "max_position_size": "3% portfolio",
                        "max_risk_per_trade": "1.5% portfolio",
                    },
                    "monitoring": [
                        "Review position at market close",
                        "Monitor news flow",
                    ],
                    "timeframe": "within 4 hours",
                },
            },
            "volume_spike": {
                "critical": {
                    "risk_management": {
                        "check_liquidity": True,
                        "avoid_large_orders": True,
                        "use_limit_orders": True,
                    },
                    "monitoring": [
                        "Assess if volume spike is sustained",
                        "Check for block trades",
                        "Monitor order book depth",
                    ],
                    "timeframe": "immediate",
                },
                "high": {
                    "risk_management": {
                        "reduce_order_size": True,
                        "use_limit_orders": True,
                    },
                    "monitoring": [
                        "Track volume vs average",
                        "Monitor price action",
                    ],
                    "timeframe": "within 1 hour",
                },
            },
            "sentiment_spike": {
                "high": {
                    "risk_management": {
                        "wait_for_confirmation": True,
                        "avoid_fomo": True,
                    },
                    "monitoring": [
                        "Verify sentiment with price action",
                        "Check multiple news sources",
                        "Assess if sentiment is justified",
                    ],
                    "timeframe": "within 2 hours",
                },
            },
            "geopolitical": {
                "critical": {
                    "risk_management": {
                        "reduce_exposure": "50%",
                        "widen_stops": True,
                        "avoid_new_positions": True,
                    },
                    "monitoring": [
                        "Follow official statements",
                        "Monitor diplomatic developments",
                        "Track safe-haven flows",
                        "Watch for escalation/de-escalation",
                    ],
                    "timeframe": "immediate",
                    "expected_duration": "24-72 hours",
                },
            },
        }

    def get_strategy(
        self, alert_type: str, severity: str
    ) -> dict[str, Any]:
        """Get emergency strategy for alert type and severity.

        Args:
            alert_type: Type of alert
            severity: Severity level

        Returns:
            Emergency strategy
        """
        alert_strategies = self._strategies.get(alert_type, {})
        strategy = alert_strategies.get(severity, {})

        # Return default if not found
        if not strategy:
            return {
                "risk_management": {
                    "maintain_discipline": True,
                    "follow_trading_plan": True,
                },
                "monitoring": ["Monitor situation closely"],
                "timeframe": "as needed",
            }

        return strategy

    def get_all_strategies(self) -> dict[str, dict[str, Any]]:
        """Get all emergency strategies.

        Returns:
            All strategies
        """
        return self._strategies

    def add_strategy(
        self,
        alert_type: str,
        severity: str,
        strategy: dict[str, Any],
    ) -> None:
        """Add or update an emergency strategy.

        Args:
            alert_type: Type of alert
            severity: Severity level
            strategy: Strategy definition
        """
        if alert_type not in self._strategies:
            self._strategies[alert_type] = {}

        self._strategies[alert_type][severity] = strategy
