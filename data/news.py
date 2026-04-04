"""
data/news.py — News fetching via NewsAPI or GDELT fallback.
# TODO: Dev3 — implement live news fetching
"""
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Map yfinance ticker → plain English search term for news APIs
_SYMBOL_KEYWORDS = {
    "GC=F": "gold commodity",
    "SI=F": "silver commodity",
    "CL=F": "crude oil WTI",
    "NG=F": "natural gas commodity",
    "ZW=F": "wheat commodity",
    "HG=F": "copper commodity",
}


def get_news(symbol: str, limit: int = 10) -> list[dict]:
    """
    Fetch news articles for a commodity symbol.

    Uses NewsAPI if NEWS_API_KEY is set, otherwise falls back to GDELT.
    Each dict has keys: title, sentiment, source, timestamp, summary.

    # TODO: Dev3 — implement sentiment scoring (positive/negative/neutral)
    # TODO: Dev3 — add caching to avoid hitting rate limits
    """
    keyword = _SYMBOL_KEYWORDS.get(symbol, symbol)

    if config.NEWS_API_KEY:
        return _fetch_newsapi(keyword, limit)
    elif config.GDELT_ENABLED:
        return _fetch_gdelt(keyword, limit)
    else:
        logger.warning("No news source configured for %s — returning empty list", symbol)
        return []


def _fetch_newsapi(keyword: str, limit: int) -> list[dict]:
    """
    Fetch from NewsAPI.org.
    # TODO: Dev3 — implement this function
    """
    import requests

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": keyword,
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": config.NEWS_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {
                "title": a.get("title", ""),
                "sentiment": "neutral",  # TODO: Dev3 — add sentiment analysis
                "source": a.get("source", {}).get("name", "Unknown"),
                "timestamp": a.get("publishedAt", "")[:16].replace("T", " "),
                "summary": a.get("description", ""),
            }
            for a in articles
        ]
    except Exception as exc:
        logger.error("NewsAPI request failed: %s", exc)
        return []


def _fetch_gdelt(keyword: str, limit: int) -> list[dict]:
    """
    Fetch from GDELT Project API (free, no key required).
    # TODO: Dev3 — implement GDELT parsing
    """
    logger.info("GDELT fetch not yet implemented, returning empty list")
    return []
