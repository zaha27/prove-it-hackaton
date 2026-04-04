"""Price data model definitions."""

from datetime import datetime

from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """OHLCV price data for a commodity."""

    commodity: str = Field(..., description="Commodity symbol")
    dates: list[str] = Field(..., description="List of dates (YYYY-MM-DD)")
    open: list[float] = Field(..., description="Opening prices")
    high: list[float] = Field(..., description="High prices")
    low: list[float] = Field(..., description="Low prices")
    close: list[float] = Field(..., description="Closing prices")
    volume: list[int] = Field(..., description="Trading volumes")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "dates": ["2024-01-01", "2024-01-02"],
                "open": [2000.0, 2010.0],
                "high": [2010.0, 2020.0],
                "low": [1990.0, 2000.0],
                "close": [2005.0, 2015.0],
                "volume": [100000, 120000],
            }
        }

    def latest_price(self) -> float:
        """Get the latest closing price."""
        if not self.close:
            return 0.0
        return self.close[-1]

    def price_change_24h(self) -> tuple[float, float]:
        """Calculate 24h price change (absolute, percentage)."""
        if len(self.close) < 2:
            return 0.0, 0.0
        current = self.close[-1]
        previous = self.close[-2]
        change = current - previous
        pct_change = (change / previous) * 100 if previous != 0 else 0.0
        return change, pct_change

    def to_dataframe(self) -> "pd.DataFrame":
        """Convert to pandas DataFrame."""
        import pandas as pd

        return pd.DataFrame({
            "Date": self.dates,
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
        })
