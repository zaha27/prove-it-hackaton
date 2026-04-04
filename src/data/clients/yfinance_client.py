"""YFinance client for fetching price and news data."""

from datetime import datetime, timedelta

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.data.config import config
from src.data.models.price import PriceData
from src.data.models.news import NewsArticle


class YFinanceClient:
    """Client for fetching commodity price data from Yahoo Finance."""

    def __init__(self) -> None:
        """Initialize the YFinance client."""
        self.symbols = config.commodity_symbols

    def fetch_ohlcv(
        self,
        commodity: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> PriceData:
        """Fetch OHLCV data for a commodity.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            PriceData object with OHLCV data

        Raises:
            ValueError: If commodity is not supported
        """
        if commodity not in self.symbols:
            raise ValueError(
                f"Unsupported commodity: {commodity}. "
                f"Supported: {list(self.symbols.keys())}"
            )

        yf_symbol = self.symbols[commodity]

        try:
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                raise ValueError(f"No data returned for {commodity} ({yf_symbol})")

            # Convert to lists
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]
            open_prices = hist["Open"].tolist()
            high_prices = hist["High"].tolist()
            low_prices = hist["Low"].tolist()
            close_prices = hist["Close"].tolist()
            volumes = hist["Volume"].tolist()

            return PriceData(
                commodity=commodity,
                dates=dates,
                open=open_prices,
                high=high_prices,
                low=low_prices,
                close=close_prices,
                volume=volumes,
            )

        except Exception as e:
            raise ValueError(f"Failed to fetch data for {commodity}: {e}") from e

    def fetch_latest_price(self, commodity: str) -> tuple[float, float]:
        """Fetch the latest price and change for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            Tuple of (current_price, change_percent)
        """
        data = self.fetch_ohlcv(commodity, period="5d")
        if not data.close:
            return 0.0, 0.0

        current = data.close[-1]
        change_pct = 0.0

        if len(data.close) > 1:
            previous = data.close[-2]
            change_pct = ((current - previous) / previous) * 100

        return current, change_pct

    def fetch_intraday(
        self, commodity: str, interval: str = "1h"
    ) -> PriceData:
        """Fetch intraday data for a commodity.

        Args:
            commodity: Commodity symbol
            interval: Intraday interval (1m, 2m, 5m, 15m, 30m, 60m, 1h)

        Returns:
            PriceData with intraday prices
        """
        # For intraday, we need to use a shorter period
        period = "1d" if interval in ["1m", "2m", "5m", "15m", "30m"] else "5d"
        return self.fetch_ohlcv(commodity, period=period, interval=interval)

    def fetch_news(
        self,
        commodity: str,
        limit: int = 10,
    ) -> list[NewsArticle]:
        """Fetch news articles for a commodity from Yahoo Finance.

        Args:
            commodity: Commodity symbol (e.g., "GOLD", "OIL")
            limit: Maximum number of articles to return

        Returns:
            List of NewsArticle objects with sentiment analysis
        """
        if commodity not in self.symbols:
            raise ValueError(
                f"Unsupported commodity: {commodity}. "
                f"Supported: {list(self.symbols.keys())}"
            )

        yf_symbol = self.symbols[commodity]
        analyzer = SentimentIntensityAnalyzer()

        try:
            ticker = yf.Ticker(yf_symbol)
            news = ticker.news or []

            articles = []
            for item in news[:limit]:
                title = item.get("title", "")
                summary = item.get("summary", "")
                content = f"{title} {summary}"

                # Analyze sentiment using VADER
                sentiment_scores = analyzer.polarity_scores(content)
                compound = sentiment_scores["compound"]

                if compound >= 0.05:
                    sentiment = "positive"
                elif compound <= -0.05:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"

                article = NewsArticle(
                    id=f"yahoo_{item.get('uuid', '')[:12]}",
                    title=title,
                    source=item.get("publisher", "Yahoo Finance"),
                    date=datetime.fromtimestamp(
                        item.get("published", 0)
                    ).strftime("%Y-%m-%d") if item.get("published") else datetime.now().strftime("%Y-%m-%d"),
                    content=summary,
                    url=item.get("link", ""),
                    sentiment=sentiment,
                    sentiment_score=compound,
                    commodity=commodity,
                    fetched_at=datetime.utcnow(),
                )
                articles.append(article)

            return articles

        except Exception as e:
            raise ValueError(f"Failed to fetch news for {commodity}: {e}") from e

    def analyze_news_sentiment(self, articles: list[NewsArticle]) -> dict:
        """Analyze overall sentiment from news articles.

        Args:
            articles: List of NewsArticle objects

        Returns:
            dict with overall_sentiment, average_score, counts
        """
        if not articles:
            return {
                "overall_sentiment": "neutral",
                "average_score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "total": 0,
            }

        scores = [a.sentiment_score for a in articles]
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
            "total": len(articles),
        }
