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
    "You are an elite, institutional Macroeconomic Risk Manager.\n"
    "CRITICAL RULES:\n"
    "1. MAX LENGTH: You must respond in maximum 3 concise sentences. Be punchy and direct.\n"
    "2. USER ALIGNMENT: You MUST strictly obey the user's Risk Profile and Investment Horizon.\n"
    "3. NO SHORTING FOR HODLERS: If the user has a Long-Term horizon (Years/HODL), NEVER recommend short-term trading or 'Short' positions. "
    "Advise to 'ACCUMULATE', 'HOLD', or 'REDUCE EXPOSURE'.\n"
    "4. OVERRIDE: If the XGBoost signal is risky but the user is Conservative, OVERRIDE the signal and recommend HOLD.\n"
    "You must briefly justify your call based on their profile."
)

_PROMPT_TEMPLATE = """USER RISK PROFILE: {risk_profile} (1-Conservative, 3-Balanced, 5-Aggressive)
XGBOOST PREDICTION: {xgboost_pred_pct}% (Confidence: {xgb_confidence})
MACRO CONTEXT: {news_summary}
Give the final verdict."""

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
            max_tokens=min(int(os.getenv("LLM_MAX_TOKENS", "150")), 200),
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

    # User profile context
    if user_profile:
        from data.user_manager import UserManager
        profile_context = f"\n## User Risk Profile\n{UserManager.get_deepseek_context(user_profile)}\n"
    else:
        profile_context = ""

    return _PROMPT_TEMPLATE.format(
        risk_profile=risk_profile,
        xgboost_pred_pct=xgb_prediction_str,
        xgb_confidence=xgb_confidence_str,
        news_summary=news_summary,
    ) + profile_context
