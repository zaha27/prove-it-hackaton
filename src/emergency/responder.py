"""Emergency responder for handling black swan events."""

from typing import Any

from src.data.clients.deepseek_client import DeepSeekClient
from src.data.services.price_service import PriceService
from src.emergency.detector import EmergencyAlert
from src.emergency.strategies import EmergencyStrategies


class EmergencyResponder:
    """Responds to emergency market events."""

    def __init__(self) -> None:
        """Initialize the emergency responder."""
        self.price_service = PriceService()
        self.llm_client = DeepSeekClient()
        self.emergency_strategies = EmergencyStrategies()

    def respond(self, alert: EmergencyAlert) -> dict[str, Any]:
        """Generate emergency response for an alert.

        Args:
            alert: Emergency alert

        Returns:
            Emergency response
        """
        # Get current market data
        current_price = self._get_current_price(alert.commodity)

        # Select pre-computed emergency strategy
        strategy = self.emergency_strategies.get_strategy(
            alert.alert_type, alert.severity
        )

        # Generate immediate recommendation
        if alert.severity in ["high", "critical"]:
            recommendation = self._generate_urgent_recommendation(alert, current_price)
        else:
            recommendation = self._generate_standard_recommendation(alert, current_price)

        return {
            "alert": {
                "type": alert.alert_type,
                "severity": alert.severity,
                "commodity": alert.commodity,
                "description": alert.description,
            },
            "current_price": current_price,
            "immediate_action": recommendation,
            "risk_management": strategy.get("risk_management", {}),
            "monitoring_instructions": strategy.get("monitoring", []),
            "timestamp": alert.timestamp.isoformat(),
            "requires_manual_review": alert.severity == "critical",
        }

    def respond_multiple(
        self, alerts: list[EmergencyAlert]
    ) -> dict[str, Any]:
        """Respond to multiple emergency alerts.

        Args:
            alerts: List of alerts

        Returns:
            Combined response
        """
        if not alerts:
            return {"has_emergency": False}

        # Group by commodity
        by_commodity: dict[str, list[EmergencyAlert]] = {}
        for alert in alerts:
            if alert.commodity not in by_commodity:
                by_commodity[alert.commodity] = []
            by_commodity[alert.commodity].append(alert)

        # Generate response for each commodity
        responses = {}
        for commodity, commodity_alerts in by_commodity.items():
            # Use most severe alert
            severity_order = ["low", "medium", "high", "critical"]
            most_severe = max(
                commodity_alerts,
                key=lambda a: severity_order.index(a.severity)
            )
            responses[commodity] = self.respond(most_severe)

        return {
            "has_emergency": True,
            "max_severity": max(
                alerts, key=lambda a: ["low", "medium", "high", "critical"].index(a.severity)
            ).severity,
            "commodity_responses": responses,
            "general_guidance": self._get_general_emergency_guidance(),
        }

    def _generate_urgent_recommendation(
        self, alert: EmergencyAlert, current_price: float
    ) -> dict[str, Any]:
        """Generate urgent recommendation for critical events.

        Args:
            alert: Emergency alert
            current_price: Current price

        Returns:
            Urgent recommendation
        """
        if alert.alert_type == "price_spike":
            direction = "up" if "up" in alert.description else "down"

            if direction == "up":
                return {
                    "action": "CONSIDER_PROFIT_TAKING",
                    "rationale": "Large upward move may be overextended",
                    "suggested_orders": [
                        {
                            "type": "TRAILING_STOP",
                            "distance_pct": 2.0,
                            "rationale": "Protect gains while allowing upside",
                        },
                        {
                            "type": "PARTIAL_CLOSE",
                            "size_pct": 50,
                            "rationale": "Take profits on half position",
                        },
                    ],
                }
            else:
                return {
                    "action": "ASSESS_STOP_LOSSES",
                    "rationale": "Large downward move - protect capital",
                    "suggested_orders": [
                        {
                            "type": "STOP_LOSS_REVIEW",
                            "rationale": "Ensure stops are appropriate for volatility",
                        },
                        {
                            "type": "POSITION_SIZE_CHECK",
                            "rationale": "Verify position size within risk limits",
                        },
                    ],
                }

        elif alert.alert_type == "geopolitical":
            return {
                "action": "EMERGENCY_PROTOCOL",
                "rationale": "Geopolitical events can cause extreme volatility",
                "suggested_orders": [
                    {
                        "type": "REDUCE_EXPOSURE",
                        "rationale": "Decrease position sizes until clarity returns",
                    },
                    {
                        "type": "WIDE_STOPS",
                        "rationale": "Avoid getting stopped out on noise",
                    },
                ],
            }

        else:
            return {
                "action": "MONITOR_CLOSELY",
                "rationale": f"Unusual {alert.alert_type} detected",
                "suggested_orders": [
                    {
                        "type": "ALERT_SETUP",
                        "rationale": "Set alerts for further developments",
                    },
                ],
            }

    def _generate_standard_recommendation(
        self, alert: EmergencyAlert, current_price: float
    ) -> dict[str, Any]:
        """Generate standard recommendation for lower severity events.

        Args:
            alert: Emergency alert
            current_price: Current price

        Returns:
            Standard recommendation
        """
        return {
            "action": "INCREASED_VIGILANCE",
            "rationale": f"{alert.alert_type} detected - monitor closely",
            "suggested_orders": [
                {
                    "type": "ALERT_SETUP",
                    "rationale": "Set price alerts for key levels",
                },
            ],
        }

    def _get_current_price(self, commodity: str) -> float:
        """Get current price for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            Current price
        """
        try:
            price_data = self.price_service.get_price_data(commodity, period="5d")
            return price_data.close[-1] if price_data.close else 0.0
        except Exception:
            return 0.0

    def _get_general_emergency_guidance(self) -> list[str]:
        """Get general emergency guidance.

        Returns:
            List of guidance points
        """
        return [
            "Stay calm and avoid emotional decisions",
            "Verify information from multiple sources",
            "Consider reducing position sizes",
            "Ensure stop losses are appropriate",
            "Document all decisions for post-analysis",
        ]
