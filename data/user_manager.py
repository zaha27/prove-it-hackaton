"""
data/user_manager.py — Robo-Advisor user profile manager.

Persists investor preferences to user.json and exposes them
to both XGBoost (confidence thresholds) and DeepSeek (prompt context).
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PROFILE_PATH = Path(__file__).parent.parent / "user.json"

_DEFAULT_PROFILE: dict = {
    "risk_score": 3,           # 1 (Low) → 5 (High)
    "investment_horizon": 3,   # 1 (Days/Scalping) → 5 (Years/HODL)
    "market_familiarity": 3,   # 1 (Novice) → 5 (Pro)
    "preferred_strategy": "Balanced",
}

# XGBoost confidence threshold per risk_score.
# Conservative investors need higher certainty before acting.
_XGB_CONFIDENCE_THRESHOLDS: dict[int, float] = {
    1: 0.90,   # Very conservative — only act on very high-confidence signals
    2: 0.80,
    3: 0.70,   # Balanced default
    4: 0.60,
    5: 0.50,   # Aggressive — act even on moderate confidence
}

# Human-readable labels for the prompts
_HORIZON_LABELS = {1: "days (scalping)", 2: "weeks", 3: "months", 4: "1-2 years", 5: "years (long-term HODL)"}
_FAMILIARITY_LABELS = {1: "novice", 2: "beginner", 3: "intermediate", 4: "advanced", 5: "professional trader"}
_RISK_LABELS = {1: "very conservative", 2: "conservative", 3: "balanced", 4: "growth-oriented", 5: "aggressive"}


class UserManager:
    """Load / save the investor profile from user.json."""

    @staticmethod
    def load_profile() -> dict:
        """Return the stored profile, or the default Balanced profile if missing."""
        try:
            if _PROFILE_PATH.exists():
                with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Fill missing keys with defaults
                profile = {**_DEFAULT_PROFILE, **data}
                return profile
        except Exception as exc:
            logger.warning("Failed to load user profile: %s — using defaults", exc)
        return dict(_DEFAULT_PROFILE)

    @staticmethod
    def save_profile(data: dict) -> None:
        """Persist profile to user.json, merging with existing defaults."""
        profile = {**_DEFAULT_PROFILE, **data}
        try:
            with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)
            logger.info("User profile saved: %s", profile)
        except Exception as exc:
            logger.error("Failed to save user profile: %s", exc)

    @staticmethod
    def profile_exists() -> bool:
        """Return True if user.json exists on disk."""
        return _PROFILE_PATH.exists()

    @staticmethod
    def get_xgb_confidence_threshold(profile: dict) -> float:
        """
        Return the minimum XGBoost confidence required to issue a BUY/SELL signal.
        Conservative users need >85% certainty; aggressive users accept 50%.
        """
        risk = int(profile.get("risk_score", 3))
        risk = max(1, min(5, risk))
        return _XGB_CONFIDENCE_THRESHOLDS[risk]

    @staticmethod
    def get_deepseek_context(profile: dict) -> str:
        """
        Build the user-context paragraph injected into the DeepSeek prompt.
        """
        risk = int(profile.get("risk_score", 3))
        horizon = int(profile.get("investment_horizon", 3))
        familiarity = int(profile.get("market_familiarity", 3))
        strategy = profile.get("preferred_strategy", "Balanced")

        risk_label = _RISK_LABELS.get(risk, "balanced")
        horizon_label = _HORIZON_LABELS.get(horizon, "months")
        familiarity_label = _FAMILIARITY_LABELS.get(familiarity, "intermediate")

        return (
            f"User Profile: {risk_label} investor (risk score {risk}/5), "
            f"investment horizon of {horizon}/5 ({horizon_label}), "
            f"market familiarity {familiarity}/5 ({familiarity_label}), "
            f"preferred strategy: {strategy}. "
            f"Tailor your advice specifically to these constraints. "
            f"{'Use simple language and focus on risk management.' if familiarity <= 2 else ''}"
            f"{'Assume advanced knowledge; include technical detail.' if familiarity >= 4 else ''}"
        ).strip()

    @staticmethod
    def get_risk_profile_string(profile: dict) -> str:
        """Return the legacy risk profile string for backward compat."""
        risk = int(profile.get("risk_score", 3))
        if risk <= 1:
            return "Conservative"
        elif risk <= 2:
            return "Conservative"
        elif risk <= 3:
            return "Balanced"
        elif risk <= 4:
            return "Aggressive"
        else:
            return "Aggressive"
