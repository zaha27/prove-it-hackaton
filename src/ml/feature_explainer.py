"""Feature explanation and correlation descriptions for XGBoost predictions."""

from typing import Any

# Feature correlation descriptions for public presentation
FEATURE_CORRELATIONS: dict[str, dict[str, Any]] = {
    # Momentum indicators
    "rsi_14": {
        "name": "RSI (14-day)",
        "description": "Relative Strength Index measuring momentum",
        "thresholds": {"low": 30, "high": 70},
        "interpretations": {
            "low": "Oversold conditions suggest potential bounce",
            "medium": "Neutral momentum - balanced buying/selling",
            "high": "Overbought conditions suggest potential pullback",
        },
    },
    "rsi_7": {
        "name": "RSI (7-day)",
        "description": "Short-term momentum indicator",
        "thresholds": {"low": 30, "high": 70},
        "interpretations": {
            "low": "Short-term oversold - possible quick recovery",
            "medium": "Neutral short-term momentum",
            "high": "Short-term overbought - watch for reversal",
        },
    },
    "macd": {
        "name": "MACD",
        "description": "Moving Average Convergence Divergence",
        "thresholds": {"low": -0.5, "high": 0.5},
        "interpretations": {
            "low": "Bearish momentum - potential downtrend",
            "medium": "Neutral trend direction",
            "high": "Bullish momentum - potential uptrend",
        },
    },
    "macd_signal": {
        "name": "MACD Signal",
        "description": "MACD signal line for trend confirmation",
        "thresholds": {"low": -0.5, "high": 0.5},
        "interpretations": {
            "low": "Confirmed bearish signal",
            "medium": "Trend unclear",
            "high": "Confirmed bullish signal",
        },
    },
    "macd_hist": {
        "name": "MACD Histogram",
        "description": "MACD momentum strength",
        "thresholds": {"low": -0.3, "high": 0.3},
        "interpretations": {
            "low": "Decreasing momentum",
            "medium": "Stable momentum",
            "high": "Increasing momentum",
        },
    },
    # Volatility indicators
    "bb_pct": {
        "name": "Bollinger Band %",
        "description": "Position within Bollinger Bands (0-1)",
        "thresholds": {"low": 0.2, "high": 0.8},
        "interpretations": {
            "low": "Price near lower band - support likely",
            "medium": "Price in middle range - balanced",
            "high": "Price near upper band - resistance likely",
        },
    },
    "bb_width": {
        "name": "Bollinger Band Width",
        "description": "Volatility measure from Bollinger Bands",
        "thresholds": {"low": 0.05, "high": 0.15},
        "interpretations": {
            "low": "Low volatility - potential breakout coming",
            "medium": "Normal volatility",
            "high": "High volatility - large price swings",
        },
    },
    "atr_14": {
        "name": "ATR (14-day)",
        "description": "Average True Range - volatility measure",
        "thresholds": {"low": 0.02, "high": 0.05},
        "interpretations": {
            "low": "Low volatility period",
            "medium": "Normal market volatility",
            "high": "High volatility - wider stops needed",
        },
    },
    # Statistical indicators
    "zscore_20": {
        "name": "Z-Score (20-day)",
        "description": "Standard deviations from 20-day mean",
        "thresholds": {"low": -1.5, "high": 1.5},
        "interpretations": {
            "low": "Price significantly below average - value opportunity",
            "medium": "Price near historical average",
            "high": "Price significantly above average - mean reversion risk",
        },
    },
    "zscore_50": {
        "name": "Z-Score (50-day)",
        "description": "Standard deviations from 50-day mean",
        "thresholds": {"low": -1.5, "high": 1.5},
        "interpretations": {
            "low": "Long-term undervalued",
            "medium": "Price aligned with long-term trend",
            "high": "Long-term overvalued",
        },
    },
    # Volume indicators
    "volume_ratio": {
        "name": "Volume Ratio",
        "description": "Current volume vs 20-day average",
        "thresholds": {"low": 0.8, "high": 1.5},
        "interpretations": {
            "low": "Below average interest",
            "medium": "Normal trading activity",
            "high": "High interest - significant move possible",
        },
    },
    "obv": {
        "name": "OBV",
        "description": "On-Balance Volume trend",
        "thresholds": {"low": -0.1, "high": 0.1},
        "interpretations": {
            "low": "Volume flowing out - distribution",
            "medium": "Balanced volume flow",
            "high": "Volume flowing in - accumulation",
        },
    },
    "vwap": {
        "name": "VWAP Distance",
        "description": "Distance from Volume-Weighted Average Price",
        "thresholds": {"low": -0.02, "high": 0.02},
        "interpretations": {
            "low": "Below average institutional price",
            "medium": "Near institutional fair value",
            "high": "Above average institutional price",
        },
    },
    # Trend indicators
    "adx": {
        "name": "ADX",
        "description": "Average Directional Index - trend strength",
        "thresholds": {"low": 20, "high": 40},
        "interpretations": {
            "low": "Weak trend - range-bound market",
            "medium": "Moderate trend strength",
            "high": "Strong trend in progress",
        },
    },
    "cci": {
        "name": "CCI",
        "description": "Commodity Channel Index",
        "thresholds": {"low": -100, "high": 100},
        "interpretations": {
            "low": "Oversold conditions",
            "medium": "Normal price cycle",
            "high": "Overbought conditions",
        },
    },
    # Price action
    "consec_up": {
        "name": "Consecutive Up Days",
        "description": "Number of consecutive positive closes",
        "thresholds": {"low": 1, "high": 3},
        "interpretations": {
            "low": "No strong upward momentum",
            "medium": "Building upward pressure",
            "high": "Extended rally - caution warranted",
        },
    },
    "consec_down": {
        "name": "Consecutive Down Days",
        "description": "Number of consecutive negative closes",
        "thresholds": {"low": 1, "high": 3},
        "interpretations": {
            "low": "No strong downward pressure",
            "medium": "Building selling pressure",
            "high": "Extended decline - bounce possible",
        },
    },
    # Temporal features
    "day_of_week": {
        "name": "Day of Week",
        "description": "Trading day (0=Monday, 6=Sunday)",
        "thresholds": {},
        "interpretations": {
            "low": "Early week trading patterns",
            "medium": "Mid-week activity",
            "high": "End-of-week positioning",
        },
    },
    "month": {
        "name": "Month",
        "description": "Calendar month (1-12)",
        "thresholds": {},
        "interpretations": {
            "low": "Q1 patterns",
            "medium": "Q2-Q3 seasonal effects",
            "high": "Q4 year-end effects",
        },
    },
}


def explain_feature_value(feature_name: str, value: float) -> dict[str, Any]:
    """Get human-readable explanation for a feature value.

    Args:
        feature_name: Name of the feature
        value: Current value of the feature

    Returns:
        Dictionary with interpretation details
    """
    if feature_name not in FEATURE_CORRELATIONS:
        return {
            "name": feature_name,
            "technical_name": feature_name,
            "value": round(value, 4),
            "description": "Technical indicator",
            "interpretation": "Technical analysis factor",
            "level": "medium",
        }

    feature_info = FEATURE_CORRELATIONS[feature_name]
    thresholds = feature_info.get("thresholds", {})

    # Determine level based on thresholds
    low_thresh = thresholds.get("low", float("-inf"))
    high_thresh = thresholds.get("high", float("inf"))

    if value < low_thresh:
        level = "low"
    elif value > high_thresh:
        level = "high"
    else:
        level = "medium"

    interpretation = feature_info["interpretations"].get(
        level, "Neutral market conditions"
    )

    return {
        "name": feature_info["name"],
        "technical_name": feature_name,
        "value": round(value, 4),
        "description": feature_info["description"],
        "interpretation": interpretation,
        "level": level,
    }


def get_feature_impact(feature_name: str, value: float, importance: float) -> str:
    """Determine if a feature has positive or negative impact on price.

    Args:
        feature_name: Name of the feature
        value: Current value
        importance: XGBoost feature importance

    Returns:
        "positive", "negative", or "neutral"
    """
    # Define which feature values typically correlate with price increases
    bullish_signals = {
        "rsi_14": (30, 50),  # Recovery from oversold
        "rsi_7": (30, 50),
        "macd": (0, float("inf")),
        "macd_signal": (0, float("inf")),
        "bb_pct": (0, 0.5),  # Lower half - room to rise
        "zscore_20": (-2, 0),  # Below average - mean reversion up
        "zscore_50": (-2, 0),
        "volume_ratio": (1.2, float("inf")),  # High volume on moves
        "obv": (0, float("inf")),
        "adx": (25, float("inf")),  # Strong trend
        "cci": (-100, 0),  # Recovery from oversold
        "consec_down": (0, 2),  # Few down days - reversal coming
    }

    bearish_signals = {
        "rsi_14": (70, 100),
        "rsi_7": (70, 100),
        "macd": (float("-inf"), 0),
        "macd_signal": (float("-inf"), 0),
        "bb_pct": (0.8, 1.0),
        "zscore_20": (1.5, float("inf")),
        "zscore_50": (1.5, float("inf")),
        "cci": (100, float("inf")),
        "consec_up": (3, float("inf")),
    }

    # Check bullish
    if feature_name in bullish_signals:
        low, high = bullish_signals[feature_name]
        if low <= value <= high:
            return "positive"

    # Check bearish
    if feature_name in bearish_signals:
        low, high = bearish_signals[feature_name]
        if low <= value <= high:
            return "negative"

    return "neutral"


def format_feature_for_public(feature_data: dict[str, Any]) -> str:
    """Format a single feature explanation for public presentation.

    Args:
        feature_data: Dictionary with feature explanation data

    Returns:
        Formatted string for display
    """
    name = feature_data.get("name", feature_data.get("technical_name", "Unknown"))
    value = feature_data.get("value", 0)
    interpretation = feature_data.get("interpretation", "")
    importance = feature_data.get("importance", 0)
    impact = feature_data.get("impact", "neutral")

    impact_emoji = {"positive": "📈", "negative": "📉", "neutral": "➡️"}.get(
        impact, "➡️"
    )

    return (
        f"{impact_emoji} {name}: {value:.4f}\n"
        f"   {interpretation}\n"
        f"   [Model importance: {importance:.1%}]"
    )
