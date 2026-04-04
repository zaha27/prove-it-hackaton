"""
data/ai_engine.py — LLM-powered commodity analysis via DeepSeek + Ollama fallback.
Used only when the FastAPI backend is unavailable.
"""
import logging
import os
from typing import Optional

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
    Generate an AI insight using DeepSeek (primary) or Ollama/Gemma4 (fallback).
    Called only when the FastAPI backend is down.
    """
    prompt = _build_prompt(symbol, price_data, news)

    # 1. Try DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    if deepseek_key:
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
            logger.warning("DeepSeek fallback failed: %s — trying Ollama", exc)

    # 2. Try Ollama
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4")
    try:
        import requests
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": ollama_model, "prompt": f"{_SYSTEM_PROMPT}\n\n{prompt}", "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as exc:
        logger.error("Ollama fallback failed: %s", exc)

    return (
        "⚠️ AI analysis unavailable: backend is down, DeepSeek key missing or invalid, "
        "and Ollama is not reachable. Start the backend with: uv run server.py"
    )


def _build_prompt(symbol: str, price_data: Optional[dict], news: list[dict]) -> str:
    """Build the CoT prompt from price data and news items."""
    _SYMBOLS = {
        "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil",
        "NG=F": "Natural Gas", "ZW=F": "Wheat", "HG=F": "Copper",
    }
    symbol_name = _SYMBOLS.get(symbol, symbol)

    if price_data and price_data.get("close"):
        last5 = list(zip(price_data["dates"][-5:], price_data["close"][-5:]))
        price_summary = "\n".join(f"  {d}: {c}" for d, c in last5)
    else:
        price_summary = "  No price data available."

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
        max_tokens=os.getenv("LLM_MAX_TOKENS", "1024"),
    )
