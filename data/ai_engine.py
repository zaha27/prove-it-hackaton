"""
data/ai_engine.py — LLM-powered commodity analysis via Anthropic API.
# TODO: Dev1 — refine CoT prompt template and system prompt
"""
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior commodity market analyst with 20 years of experience. "
    "You combine technical analysis, fundamental analysis, and macro-economic context. "
    "Always structure your response as Chain-of-Thought reasoning: "
    "Step 1 (Macro context) → Step 2 (Supply/demand) → Step 3 (Technical) → Conclusion with bias. "
    "Be concise, data-driven, and avoid speculation without basis."
)

_PROMPT_TEMPLATE = """
Analyze the following commodity: {symbol_name} ({symbol})

## Recent Price Data (last 5 days)
{price_summary}

## Recent News
{news_summary}

Provide a Chain-of-Thought analysis concluding with a directional bias (bullish/bearish/neutral)
and key price levels to watch. Keep response under {max_tokens} tokens.
"""


def get_ai_insight(
    symbol: str,
    price_data: Optional[dict],
    news: list[dict],
) -> str:
    """
    Generate an AI insight for a commodity using the Anthropic API.

    # TODO: Dev1 — add streaming support for real-time token display in panel_ai
    # TODO: Dev1 — cache results with a TTL to avoid redundant API calls on re-selection
    """
    if not config.ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY not configured. Set it in .env to enable AI insights."

    prompt = _build_prompt(symbol, price_data, news)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as exc:
        logger.error("Anthropic API call failed: %s", exc)
        return f"⚠️ AI analysis unavailable: {exc}"


def _build_prompt(symbol: str, price_data: Optional[dict], news: list[dict]) -> str:
    """Build the CoT prompt from price data and news items."""
    from config import SYMBOLS

    symbol_name = SYMBOLS.get(symbol, symbol)

    # Summarise last 5 close prices
    if price_data and price_data.get("close"):
        last5 = list(zip(price_data["dates"][-5:], price_data["close"][-5:]))
        price_summary = "\n".join(f"  {d}: {c}" for d, c in last5)
    else:
        price_summary = "  No price data available."

    # Summarise news titles and sentiments
    if news:
        news_summary = "\n".join(
            f"  [{item.get('sentiment','?').upper()}] {item.get('title','')}"
            for item in news[:5]
        )
    else:
        news_summary = "  No news available."

    return _PROMPT_TEMPLATE.format(
        symbol=symbol,
        symbol_name=symbol_name,
        price_summary=price_summary,
        news_summary=news_summary,
        max_tokens=config.LLM_MAX_TOKENS,
    )
