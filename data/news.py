"""
data/news.py — News fetching via Yahoo Finance only.
"""
import logging
from datetime import datetime
import re
from urllib.parse import urlparse

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# Sentiment analyzer
_sentiment_analyzer = SentimentIntensityAnalyzer()

# Map yfinance ticker → Yahoo Finance symbol
_SYMBOL_MAP = {
    "GC=F": "GC=F",
    "SI=F": "SI=F",
    "CL=F": "CL=F",
    "NG=F": "NG=F",
    "ZW=F": "ZW=F",
    "HG=F": "HG=F",
}

_GDELT_BASE_URL = "https://api.gdeltproject.org/api/v2/context/context"
_GDELT_QUERY = "(economy OR conflict OR energy) domainis:reuters.com"
_MAX_GDELT_RESULTS = 50
_COUNTRY_KEYWORDS_ISO3 = {
    "iran": "IRN",
    "ukraine": "UKR",
    "usa": "USA",
    "china": "CHN",
}


def _extract_source(article: dict) -> str:
    source = article.get("source") or article.get("domain")
    if source:
        return str(source)

    url = article.get("url", "")
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or "Unknown"
    except Exception:
        return "Unknown"


def _normalize_timestamp(article: dict) -> str:
    raw_timestamp = (
        article.get("seendate")
        or article.get("date")
        or article.get("published")
        or article.get("timestamp")
        or ""
    )
    if not raw_timestamp:
        return ""

    raw_str = str(raw_timestamp).strip()
    try:
        if len(raw_str) == 14 and raw_str.isdigit():
            dt = datetime.strptime(raw_str, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if " " in raw_str and "T" not in raw_str:
            return raw_str.replace(" ", "T") + "Z"
        return raw_str
    except Exception:
        return raw_str


def _infer_country_iso3(title: str) -> str | None:
    lowered = (title or "").lower()
    for keyword, iso3 in _COUNTRY_KEYWORDS_ISO3.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return iso3
    return None


def _sentiment_from_text(text: str) -> tuple[str, float]:
    scores = _sentiment_analyzer.polarity_scores(text or "")
    compound = scores["compound"]
    if compound >= 0.05:
        return "positive", compound
    if compound <= -0.05:
        return "negative", compound
    return "neutral", compound


def fetch_real_world_news(limit: int = 50) -> list[dict]:
    """
    Fetch real-world macro news using GDELT Contextual Search API.

    Returns a list of dicts compatible with NewsCard UI.
    """
    safe_limit = max(1, min(int(limit), _MAX_GDELT_RESULTS))
    params = {
        "query": _GDELT_QUERY,
        "mode": "artlist",
        "maxresults": safe_limit,
        "format": "json",
    }

    try:
        resp = requests.get(_GDELT_BASE_URL, params=params, timeout=12)
        resp.raise_for_status()
        payload = resp.json()
        articles = payload.get("articles", []) if isinstance(payload, dict) else []
    except Exception as exc:
        logger.error("Failed to fetch GDELT macro news: %s", exc)
        return []

    result: list[dict] = []
    for article in articles[:safe_limit]:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        sentiment, _ = _sentiment_from_text(title)

        mapped = {
            "title": title,
            "source": _extract_source(article),
            "timestamp": _normalize_timestamp(article),
            "url": url,
            "sentiment": sentiment,
            "summary": "",
        }
        country_iso3 = _infer_country_iso3(title)
        if country_iso3:
            mapped["country_iso3"] = country_iso3
        result.append(mapped)

    return result


def get_news(symbol: str, limit: int = 10) -> list[dict]:
    """
    Fetch news articles for a commodity symbol from Yahoo Finance.

    Each dict has keys: title, sentiment, source, timestamp, summary, sentiment_score.
    """
    import yfinance as yf

    yf_symbol = _SYMBOL_MAP.get(symbol, symbol)

    try:
        ticker = yf.Ticker(yf_symbol)
        news = ticker.news or []

        articles = []
        for item in news[:limit]:
            title = item.get("title", "")
            summary = item.get("summary", "")
            content = f"{title} {summary}"

            # Analyze sentiment
            sentiment_scores = _sentiment_analyzer.polarity_scores(content)
            compound = sentiment_scores["compound"]

            if compound >= 0.05:
                sentiment = "positive"
            elif compound <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            articles.append({
                "title": title,
                "sentiment": sentiment,
                "sentiment_score": compound,
                "source": item.get("publisher", "Yahoo Finance"),
                "timestamp": item.get("published", ""),
                "summary": summary[:300] if summary else "",
                "url": item.get("link", ""),
            })

        logger.info("Fetched %d news articles for %s from Yahoo Finance", len(articles), symbol)
        return articles

    except Exception as exc:
        logger.error("Failed to fetch Yahoo Finance news for %s: %s", symbol, exc)
        return []


def analyze_news_sentiment(news_items: list[dict]) -> dict:
    """
    Analyze overall sentiment from a list of news items.

    Returns:
        dict with overall_sentiment, average_score, positive_count, negative_count, neutral_count
    """
    if not news_items:
        return {
            "overall_sentiment": "neutral",
            "average_score": 0.0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "total": 0,
        }

    scores = [item.get("sentiment_score", 0) for item in news_items]
    avg_score = sum(scores) / len(scores) if scores else 0

    positive = sum(1 for s in scores if s >= 0.05)
    negative = sum(1 for s in scores if s <= -0.05)
    neutral = len(scores) - positive - negative

    if avg_score >= 0.05:
        overall = "positive"
    elif avg_score <= -0.05:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "overall_sentiment": overall,
        "average_score": round(avg_score, 3),
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "total": len(news_items),
    }
