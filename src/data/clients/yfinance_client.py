"""YFinance client for fetching price data."""

from datetime import datetime, timedelta

import yfinance as yf

from src.data.config import config
from src.data.models.price import PriceData


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
