"""
data/market.py — Live market data via yfinance.
# TODO: Dev2 — implement live data fetching and error handling
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RANGE_MAP = {
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
    "Max": "max",
}

_INTERVAL_MAP = {
    "1D": "1d",
    "1W": "1wk",
    "1M": "1mo",
}


def get_price_data(symbol: str, range_str: str = "1y", interval_str: str = "1d") -> Optional[dict]:
    """
    Fetch OHLCV data using yfinance period + interval.

    Returns a dict with keys: symbol, currency, dates, open, high, low, close, volume.
    Returns None on failure.
    """
    try:
        import yfinance as yf

        range_mapped = _RANGE_MAP.get(range_str, range_str.lower())
        interval_mapped = _INTERVAL_MAP.get(interval_str, interval_str.lower())
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=range_mapped, interval=interval_mapped)

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
