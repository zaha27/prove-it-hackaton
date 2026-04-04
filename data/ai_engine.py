"""
data/ai_engine.py — Neuro-Symbolic insight via DeepSeek.
Used only when the FastAPI backend is unavailable.

Architecture: XGBoost (Quant) → DeepSeek (Risk Manager)
    - XGBoost prediction is the quantitative signal
    - DeepSeek validates/invalidates it against macro news
"""
import logging
import os
from typing import Optional
from data.user_manager import UserManager

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an elite, hyper-concise Quantitative Portfolio Manager. "
    "You receive an XGBoost mathematical prediction, global macro news, and the User's Risk Profile.\n"
    "YOUR RULES:\n"
    "- Maximum 4 short sentences or 3 crisp bullet points. NO rambling.\n"
    "- You MUST explicitly state how the User's Risk Profile alters the XGBoost recommendation.\n"
    "- If Risk is 'Conservative' and XGBoost predicts a small gain but news shows volatility, "
    "OVERRIDE the model and recommend HOLD/AVOID.\n"
    "- Use a cold, professional, institutional tone."
)

_PROMPT_TEMPLATE = """USER RISK PROFILE: {risk_profile} (1-Conservative, 3-Balanced, 5-Aggressive)
XGBOOST PREDICTION: {xgboost_pred_pct}% (Confidence: {xgb_confidence})
MACRO CONTEXT: {news_summary}
Give the final verdict."""

def get_ai_insight(
    symbol: str,
    xgboost_prediction: Optional[dict],
    news_list: list[dict],
) -> str:
    """
    Generate a neuro-symbolic insight using DeepSeek as Risk Manager.
    Called only when the FastAPI backend is down.

    Args:
        symbol: Commodity ticker (e.g. "GC=F")
        xgboost_prediction: Dict with keys: prediction (float), confidence (float),
                            reasoning (str), top_features (list). Pass {} if unavailable.
        news_list: List of news dicts with 'title', 'sentiment' keys.
    """
    prompt = _build_prompt(symbol, xgboost_prediction or {}, news_list)

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
            max_tokens=min(int(os.getenv("LLM_MAX_TOKENS", "150")), 200),
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.error("DeepSeek call failed for %s: %s", symbol, exc)
        return f"⚠️ AI analysis unavailable: {exc}"


def _build_prompt(symbol: str, xgboost_prediction: dict, news_list: list[dict]) -> str:
    # XGBoost signal
    prediction = float(xgboost_prediction.get("prediction", 0))
    confidence = float(xgboost_prediction.get("confidence", 0))

    xgb_prediction_str = f"{prediction:+.2%}" if xgboost_prediction else "N/A"
    xgb_confidence_str = f"{confidence:.0%}" if xgboost_prediction else "N/A"

    risk_profile = "Balanced"
    try:
        risk_profile = UserManager.get_risk_profile_string(UserManager.load_profile())
    except Exception as exc:
        logger.warning("Failed to load user risk profile for %s: %s", symbol, exc)

    # News summary
    if news_list:
        news_summary = "\n".join(
            f"  [{item.get('sentiment', '?').upper()}] {item.get('title', '')}"
            for item in news_list[:5]
        )
    else:
        news_summary = "  No news available."

    return _PROMPT_TEMPLATE.format(
        risk_profile=risk_profile,
        xgboost_pred_pct=xgb_prediction_str,
        xgb_confidence=xgb_confidence_str,
        news_summary=news_summary,
    )
