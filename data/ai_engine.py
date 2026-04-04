"""
data/ai_engine.py — Neuro-Symbolic insight via DeepSeek.
Used only when the FastAPI backend is unavailable.

Architecture: XGBoost (Quant) → DeepSeek (Risk Manager)
    - XGBoost prediction is the quantitative signal
    - DeepSeek validates/invalidates it against macro news
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a Macroeconomic Risk Manager at a commodity trading desk. "
    "You receive a quantitative prediction from an XGBoost model and a list of recent news headlines. "
    "Your role is NOT to recalculate the mathematics — the XGBoost model handles that. "
    "Your role is to validate or invalidate the XGBoost signal using fundamental macro context: "
    "geopolitical events, supply/demand shocks, central bank decisions, and news sentiment. "
    "Structure your response as: "
    "1. XGBoost Signal Summary → 2. News/Macro Context → 3. Validation or Override → 4. Final Verdict. "
    "Be concise and data-driven."
)

_PROMPT_TEMPLATE = """## XGBoost Quantitative Signal — {symbol_name} ({symbol})

**Model output:**
- Direction: {xgb_direction}
- Predicted change: {xgb_prediction}
- Confidence: {xgb_confidence}

## Recent News Headlines
{news_summary}

## Your Task
Does the macro/news context VALIDATE or CONTRADICT the XGBoost {xgb_direction} signal?
Provide your Reality Check verdict with a final recommendation (BUY / HOLD / SELL).
"""

_SYMBOLS = {
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil",
    "NG=F": "Natural Gas", "ZW=F": "Wheat", "HG=F": "Copper",
}


def get_ai_insight(
    symbol: str,
    xgboost_prediction: Optional[dict],
    news_list: list[dict],
    user_profile: Optional[dict] = None,
) -> str:
    """
    Generate a neuro-symbolic insight using DeepSeek as Risk Manager.
    Called only when the FastAPI backend is down.

    Args:
        symbol: Commodity ticker (e.g. "GC=F")
        xgboost_prediction: Dict with keys: prediction (float), confidence (float),
                            reasoning (str), top_features (list). Pass {} if unavailable.
        news_list: List of news dicts with 'title', 'sentiment' keys.
        user_profile: Optional investor profile dict from user.json.
    """
    prompt = _build_prompt(symbol, xgboost_prediction or {}, news_list, user_profile or {})

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not deepseek_key:
        return (
            "⚠️ AI analysis unavailable: DEEPSEEK_API_KEY not configured. "
            "Add it to .env and restart the server."
        )

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=deepseek_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("DeepSeek call failed for %s: %s", symbol, exc)
        return f"⚠️ AI analysis unavailable: {exc}"


def _build_prompt(symbol: str, xgboost_prediction: dict, news_list: list[dict], user_profile: dict) -> str:
    symbol_name = _SYMBOLS.get(symbol, symbol)

    # XGBoost signal
    prediction = float(xgboost_prediction.get("prediction", 0))
    confidence = float(xgboost_prediction.get("confidence", 0))

    if prediction > 0.005:
        xgb_direction = "BUY"
    elif prediction < -0.005:
        xgb_direction = "SELL"
    else:
        xgb_direction = "HOLD"

    xgb_prediction_str = f"{prediction:+.2%}" if xgboost_prediction else "N/A (no XGBoost data)"
    xgb_confidence_str = f"{confidence:.0%}" if xgboost_prediction else "N/A"

    # News summary
    if news_list:
        news_summary = "\n".join(
            f"  [{item.get('sentiment', '?').upper()}] {item.get('title', '')}"
            for item in news_list[:5]
        )
    else:
        news_summary = "  No news available."

    # User profile context
    if user_profile:
        from data.user_manager import UserManager
        profile_context = f"\n## User Risk Profile\n{UserManager.get_deepseek_context(user_profile)}\n"
    else:
        profile_context = ""

    return _PROMPT_TEMPLATE.format(
        symbol=symbol,
        symbol_name=symbol_name,
        xgb_direction=xgb_direction,
        xgb_prediction=xgb_prediction_str,
        xgb_confidence=xgb_confidence_str,
        news_summary=news_summary,
    ) + profile_context
