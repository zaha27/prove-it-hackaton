"""
data/news.py — News fetching via Yahoo Finance only.
"""
import logging
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
