"""Emergency event detector for black swan events."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from src.data.config import config
from src.data.services.news_service import NewsService
from src.data.services.price_service import PriceService


@dataclass
class EmergencyAlert:
    """Emergency alert definition."""

    commodity: str
    alert_type: str  # price_spike, volume_spike, sentiment_spike, geopolitical
    severity: str  # low, medium, high, critical
    trigger_value: float
    threshold: float
    timestamp: datetime
    description: str
    recommended_action: str


class EmergencyDetector:
    """Detects emergency market events requiring immediate response."""

    def __init__(self) -> None:
        """Initialize the emergency detector."""
        self.price_service = PriceService()
        self.news_service = NewsService()

        # Thresholds from config
        self.price_move_pct = config.emergency_price_move_pct
        self.volume_multiplier = config.emergency_volume_multiplier
        self.sentiment_spike = config.emergency_news_sentiment_spike

        # Historical baselines
        self._price_baselines: dict[str, dict[str, float]] = {}
        self._volume_baselines: dict[str, float] = {}

    def detect_all(self, commodity: str) -> list[EmergencyAlert]:
        """Detect all emergency conditions for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            List of emergency alerts
        """
        alerts = []

        # Check price spike
        price_alert = self.detect_price_spike(commodity)
        if price_alert:
            alerts.append(price_alert)

        # Check volume spike
        volume_alert = self.detect_volume_spike(commodity)
        if volume_alert:
            alerts.append(volume_alert)

        # Check sentiment spike
        sentiment_alert = self.detect_sentiment_spike(commodity)
        if sentiment_alert:
            alerts.append(sentiment_alert)

        # Check for geopolitical keywords
        geo_alert = self.detect_geopolitical_events(commodity)
        if geo_alert:
            alerts.append(geo_alert)

        return alerts

    def detect_price_spike(self, commodity: str) -> EmergencyAlert | None:
        """Detect price spike emergency.

        Args:
            commodity: Commodity symbol

        Returns:
            Emergency alert or None
        """
        try:
            # Get intraday data
            price_data = self.price_service.get_price_data(
                commodity, period="5d", interval="1h"
            )

            if not price_data.close or len(price_data.close) < 2:
                return None

            # Calculate 1-hour change
            current_price = price_data.close[-1]
            prev_price = price_data.close[-2]
            change_pct = abs((current_price / prev_price - 1) * 100)

            # Check against threshold
            if change_pct >= self.price_move_pct:
                # Determine severity
                if change_pct >= 10:
                    severity = "critical"
                elif change_pct >= 7:
                    severity = "high"
                elif change_pct >= 5:
                    severity = "medium"
                else:
                    severity = "low"

                direction = "up" if current_price > prev_price else "down"

                return EmergencyAlert(
                    commodity=commodity,
                    alert_type="price_spike",
                    severity=severity,
                    trigger_value=change_pct,
                    threshold=self.price_move_pct,
                    timestamp=datetime.utcnow(),
                    description=f"Price moved {change_pct:.1f}% {direction} in 1 hour",
                    recommended_action=self._get_price_spike_action(direction),
                )

            return None

        except Exception as e:
            print(f"Error detecting price spike: {e}")
            return None

    def detect_volume_spike(self, commodity: str) -> EmergencyAlert | None:
        """Detect volume spike emergency.

        Args:
            commodity: Commodity symbol

        Returns:
            Emergency alert or None
        """
        try:
            price_data = self.price_service.get_price_data(
                commodity, period="5d", interval="1h"
            )

            if not price_data.volume or len(price_data.volume) < 20:
                return None

            # Calculate average volume (excluding last hour)
            avg_volume = np.mean(price_data.volume[-20:-1])
            current_volume = price_data.volume[-1]

            if avg_volume == 0:
                return None

            volume_mult = current_volume / avg_volume

            if volume_mult >= self.volume_multiplier:
                severity = (
                    "critical" if volume_mult >= 10
                    else "high" if volume_mult >= 7
                    else "medium"
                )

                return EmergencyAlert(
                    commodity=commodity,
                    alert_type="volume_spike",
                    severity=severity,
                    trigger_value=volume_mult,
                    threshold=self.volume_multiplier,
                    timestamp=datetime.utcnow(),
                    description=f"Volume spiked {volume_mult:.1f}x above average",
                    recommended_action="Assess liquidity conditions immediately",
                )

            return None

        except Exception as e:
            print(f"Error detecting volume spike: {e}")
            return None

    def detect_sentiment_spike(self, commodity: str) -> EmergencyAlert | None:
        """Detect news sentiment spike.

        Args:
            commodity: Commodity symbol

        Returns:
            Emergency alert or None
        """
        try:
            # Get recent news
            news = self.news_service.get_news_for_commodity(
                commodity, days=1, limit=20
            )

            if not news:
                return None

            # Calculate sentiment scores
            scores = [article.sentiment_score for article in news]
            avg_sentiment = np.mean(scores)
            std_sentiment = np.std(scores)

            # Check for extreme sentiment
            max_sentiment = max(abs(min(scores)), abs(max(scores)))

            if max_sentiment > 0.8:  # Very strong sentiment
                # Check if it's a spike (compared to recent average)
                if std_sentiment > 0.3:
                    severity = "high" if max_sentiment > 0.9 else "medium"
                    sentiment_type = "positive" if max(scores) > abs(min(scores)) else "negative"

                    return EmergencyAlert(
                        commodity=commodity,
                        alert_type="sentiment_spike",
                        severity=severity,
                        trigger_value=max_sentiment,
                        threshold=0.8,
                        timestamp=datetime.utcnow(),
                        description=f"Extreme {sentiment_type} sentiment detected in news",
                        recommended_action=f"Monitor for {sentiment_type} price momentum",
                    )

            return None

        except Exception as e:
            print(f"Error detecting sentiment spike: {e}")
            return None

    def detect_geopolitical_events(self, commodity: str) -> EmergencyAlert | None:
        """Detect geopolitical events from news.

        Args:
            commodity: Commodity symbol

        Returns:
            Emergency alert or None
        """
        try:
            news = self.news_service.get_news_for_commodity(
                commodity, days=1, limit=10
            )

            if not news:
                return None

            # Keywords indicating geopolitical events
            geo_keywords = [
                "war", "attack", "strike", "sanctions", "embargo",
                "invasion", "missile", "bombing", "terrorist", "hostage",
                "diplomatic crisis", "trade war", "export ban", "supply disruption",
            ]

            for article in news:
                title_lower = article.title.lower()
                content_lower = (article.content or "").lower()

                for keyword in geo_keywords:
                    if keyword in title_lower or keyword in content_lower:
                        return EmergencyAlert(
                            commodity=commodity,
                            alert_type="geopolitical",
                            severity="critical",
                            trigger_value=1.0,
                            threshold=0.0,
                            timestamp=datetime.utcnow(),
                            description=f"Geopolitical event detected: {article.title[:100]}...",
                            recommended_action="Immediate assessment required - consider emergency protocols",
                        )

            return None

        except Exception as e:
            print(f"Error detecting geopolitical events: {e}")
            return None

    def _get_price_spike_action(self, direction: str) -> str:
        """Get recommended action for price spike.

        Args:
            direction: up or down

        Returns:
            Recommended action
        """
        if direction == "up":
            return "Consider taking profits or trailing stops"
        else:
            return "Assess stop losses and position sizing"

    def get_emergency_summary(self, alerts: list[EmergencyAlert]) -> dict[str, Any]:
        """Get summary of emergency alerts.

        Args:
            alerts: List of alerts

        Returns:
            Summary
        """
        if not alerts:
            return {
                "has_emergency": False,
                "max_severity": None,
                "alert_count": 0,
            }

        severity_order = ["low", "medium", "high", "critical"]
        max_severity = max(
            alerts,
            key=lambda a: severity_order.index(a.severity)
        ).severity

        return {
            "has_emergency": True,
            "max_severity": max_severity,
            "alert_count": len(alerts),
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "description": a.description,
                }
                for a in alerts
            ],
        }
