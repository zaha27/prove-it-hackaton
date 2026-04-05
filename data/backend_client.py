"""
data/backend_client.py — HTTP client for the local FastAPI backend (server.py).

Adapts backend API responses to the exact dict format expected by the frontend
(chart_engine, panel_news, panel_ai) so bridge.py can swap transparently.

Backend endpoints used:
    GET  /health
    GET  /api/v1/price/data/{commodity}?period=1y&interval=1d
    GET  /api/v1/price/latest/{commodity}
    GET  /api/v1/sentiment/news/{commodity}?days=7&limit=10
    POST /api/v1/mcp/insight  (AI insight via MCP/DeepSeek)
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_TIMEOUT_FAST = 3    # health check
_TIMEOUT_DATA = 12   # price / news
_TIMEOUT_AI   = 45   # AI insight (LLM can be slow)

# Frontend yfinance tickers → backend commodity names (src/data/config.py)
_TICKER_TO_BACKEND: dict[str, str] = {
    "GC=F": "GOLD",
    "SI=F": "SILVER",
    "CL=F": "OIL",
    "NG=F": "NATURAL_GAS",
    "ZW=F": "WHEAT",
    "HG=F": "COPPER",
}

# Frontend timeframe range strings → yfinance period strings
_RANGE_TO_PERIOD: dict[str, str] = {
    "6M":  "6mo",
    "1Y":  "1y",
    "5Y":  "5y",
    "Max": "max",
}

# Backend sentiment labels → frontend labels
_SENTIMENT_MAP: dict[str, str] = {
    "positive": "bullish",
    "negative": "bearish",
    "neutral":  "neutral",
}


# ── Health ─────────────────────────────────────────────────────────────────────

def is_backend_available() -> bool:
    """Return True if the FastAPI backend is reachable at BACKEND_URL."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=_TIMEOUT_FAST)
        return resp.status_code == 200
    except Exception:
        return False


# ── Price data ─────────────────────────────────────────────────────────────────

def get_price_data(
    symbol: str,
    range_str: str = "1Y",
    interval_str: str = "1D",
) -> dict | None:
    """
    Fetch OHLCV data from backend and return in chart_engine format:
        {symbol, currency, dates[], open[], high[], low[], close[], volume[]}

    Returns None on any error so bridge.py can fall back to direct yfinance.
    """
    commodity = _TICKER_TO_BACKEND.get(symbol)
    if not commodity:
        logger.warning("No backend mapping for symbol %s", symbol)
        return None

    _INTERVAL_MAP = {"1D": "1d", "1W": "1wk", "1M": "1mo"}
    period   = _RANGE_TO_PERIOD.get(range_str, "1y")
    interval = _INTERVAL_MAP.get(interval_str, interval_str.lower())

    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/price/data/{commodity}",
            params={"period": period, "interval": interval},
            timeout=_TIMEOUT_DATA,
        )
        resp.raise_for_status()
        raw = resp.json()

        # Backend shape: {commodity, data: [{timestamp, open, high, low, close, volume}]}
        points = raw.get("data", [])
        if not points:
            logger.warning("Backend returned empty price data for %s", symbol)
            return None

        return {
            "symbol":   symbol,
            "currency": "USD",
            "dates":    [p["timestamp"][:10] for p in points],   # ISO → YYYY-MM-DD
            "open":     [float(p["open"])     for p in points],
            "high":     [float(p["high"])     for p in points],
            "low":      [float(p["low"])      for p in points],
            "close":    [float(p["close"])    for p in points],
            "volume":   [int(p["volume"])     for p in points],
        }

    except Exception as exc:
        logger.error("backend get_price_data failed for %s: %s", symbol, exc)
        return None


def get_latest_price(symbol: str) -> float | None:
    """Fetch the single latest price for the status bar."""
    commodity = _TICKER_TO_BACKEND.get(symbol)
    if not commodity:
        return None
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/price/latest/{commodity}",
            timeout=_TIMEOUT_DATA,
        )
        resp.raise_for_status()
        return float(resp.json()["current_price"])
    except Exception as exc:
        logger.error("backend get_latest_price failed for %s: %s", symbol, exc)
        return None


# ── News / sentiment ───────────────────────────────────────────────────────────

def get_news(symbol: str) -> list[dict]:
    """
    Fetch news from backend and return in panel_news format:
        [{title, sentiment, source, timestamp, summary}]

    Returns [] on error so bridge.py can fall back to direct NewsAPI call.
    """
    commodity = _TICKER_TO_BACKEND.get(symbol)
    if not commodity:
        return []

    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/sentiment/news/{commodity}",
            params={"days": 7, "limit": 10},
            timeout=_TIMEOUT_DATA,
        )
        resp.raise_for_status()
        raw = resp.json()

        # Backend shape: {commodity, articles: [NewsArticle], total_count, fetched_at}
        articles = raw.get("articles", [])
        result = []
        for a in articles:
            result.append({
                "title":     a.get("title", ""),
                "sentiment": _SENTIMENT_MAP.get(a.get("sentiment", "neutral"), "neutral"),
                "source":    a.get("source", ""),
                "timestamp": a.get("date", ""),
                "summary":   (a.get("content") or "")[:300],
            })
        return result

    except Exception as exc:
        logger.error("backend get_news failed for %s: %s", symbol, exc)
        return []


# ── Macro events (pentru World Map) ───────────────────────────────────────────

def get_macro_events() -> list[dict]:
    """
    Fetch geo-located macro events from the backend for the World Map.
    Returns list of dicts matching WorldMapWidget contract:
        [{title, lat, lon, severity, category, country, summary}]
    Returns [] on error (world map will stay empty).
    """
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/v1/price/macro-events",
            timeout=_TIMEOUT_DATA,
        )
        resp.raise_for_status()
        return resp.json().get("events", [])
    except Exception as exc:
        logger.error("backend get_macro_events failed: %s", exc)
        return []


# ── AI insight (via /api/v1/mcp/insight) ─────────────────────────────────────

def get_ai_insight(symbol: str, price_data: dict | None, news: list[dict]) -> str:
    """
    Request an AI insight from the backend MCP endpoint.
    Falls back to Ollama (local) if backend unavailable or fails.

    Backend shape returned: {commodity, insight: {summary, key_factors, price_outlook,
                             recommendation, sentiment, confidence, model}, ...}
    We format it into the Chain-of-Thought markdown string the UI expects.
    """
    commodity = _TICKER_TO_BACKEND.get(symbol, symbol)

    # Build a short news summary to send upstream
    news_summary = "; ".join(
        f"{n['title']} ({n['sentiment']})" for n in (news or [])[:3]
    )

    price_dict: dict = {}
    if price_data and price_data.get("close"):
        closes = price_data["close"]
        price_dict = {
            "current": closes[-1] if closes else 0,
            "change_5d_pct": round(
                (closes[-1] - closes[-5]) / closes[-5] * 100, 2
            ) if len(closes) >= 5 else 0,
        }

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/mcp/insight",
            json={
                "commodity":   commodity,
                "price_data":  price_dict,
                "news_summary": news_summary,
                "use_mcp":     True,
            },
            timeout=_TIMEOUT_AI,
        )
        resp.raise_for_status()
        data   = resp.json()
        insight = data.get("insight", {})

        # Format into the markdown Chain-of-Thought string the UI renders
        summary    = insight.get("summary", "")
        factors    = insight.get("key_factors", [])
        outlook    = insight.get("price_outlook", "")
        rec        = insight.get("recommendation", "")
        sentiment  = insight.get("sentiment", "")
        confidence = insight.get("confidence", 0)
        model      = insight.get("model", "backend")

        lines = [f"**AI Insight — {symbol}** *(via {model})*\n"]
        if summary:
            lines.append(f"{summary}\n")
        if factors:
            lines.append("**Key Factors:**")
            for f in factors:
                lines.append(f"- {f}")
            lines.append("")
        if outlook:
            lines.append(f"**Price Outlook:** {outlook}\n")
        if rec:
            lines.append(f"**Recommendation:** {rec}")
        if sentiment:
            lines.append(f"**Sentiment:** {sentiment}  |  Confidence: {confidence:.0%}")

        return "\n".join(lines)

    except Exception as exc:
        logger.warning(
            "backend get_ai_insight failed for %s (%s) — backend unavailable",
            symbol, exc,
        )
        return f"AI insight unavailable: backend returned an error ({exc}). Make sure the server is running."


# ── Consensus (via /api/v1/mcp/consensus) ─────────────────────────────────────

def get_consensus(
    symbol: str,
    max_rounds: int = 3,
    user_profile: dict | None = None,
) -> dict | None:
    """
    Request XGBoost → DeepSeek neuro-symbolic analysis from the backend.

    Args:
        symbol: Frontend ticker (e.g. "GC=F")
        max_rounds: Max rounds (kept for API compat)
        user_profile: Full investor profile dict from user.json

    Returns dict with analysis result and final recommendation, or None on error.
    """
    from data.user_manager import UserManager
    profile = user_profile or UserManager.load_profile()
    commodity = _TICKER_TO_BACKEND.get(symbol, symbol)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/mcp/consensus/{commodity}",
            params={"max_rounds": max_rounds, "agreement_threshold": 0.8},
            json={
                "risk_profile": UserManager.get_risk_profile_string(profile),
                "risk_score": profile.get("risk_score", 3),
                "investment_horizon": profile.get("investment_horizon", 3),
                "market_familiarity": profile.get("market_familiarity", 3),
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    except Exception as exc:
        logger.error("backend get_consensus failed for %s: %s", symbol, exc)
        return None
