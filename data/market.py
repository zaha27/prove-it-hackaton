"""
data/market.py — Live market data via yfinance.
# TODO: Dev2 — implement live data fetching and error handling
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def get_price_data(symbol: str, period_days: int = 30) -> Optional[dict]:
    """
    Fetch OHLCV data for the last `period_days` days using yfinance.

    Returns a dict with keys: symbol, currency, dates, open, high, low, close, volume.
    Returns None on failure.

    # TODO: Dev2 — add period_days → yfinance interval mapping (1W=1d, 1M=1d, 3M=1d, 6M=1wk, 1Y=1wk)
    """
    try:
        import yfinance as yf

        end = datetime.today()
        start = end - timedelta(days=period_days)
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

        if df.empty:
            logger.warning("yfinance returned empty DataFrame for %s", symbol)
            return None

        return {
            "symbol": symbol,
            "currency": ticker.fast_info.get("currency", "USD"),
            "dates": df.index.strftime("%Y-%m-%d").tolist(),
            "open": df["Open"].round(3).tolist(),
            "high": df["High"].round(3).tolist(),
            "low": df["Low"].round(3).tolist(),
            "close": df["Close"].round(3).tolist(),
            "volume": df["Volume"].tolist(),
        }
    except Exception as exc:
        logger.error("Failed to fetch price data for %s: %s", symbol, exc)
        return None


def get_current_price(symbol: str) -> Optional[float]:
    """
    Fetch the latest price for a symbol.

    Returns None on failure.

    # TODO: Dev2 — consider caching to avoid rate-limiting on frequent refreshes
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.get("last_price")
        if price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return round(float(price), 3) if price else None
    except Exception as exc:
        logger.error("Failed to fetch current price for %s: %s", symbol, exc)
        return None
