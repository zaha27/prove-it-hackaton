"""Price module Pydantic models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PricePoint(BaseModel):
    """Single price point."""

    timestamp: datetime = Field(..., description="Timestamp of the price point")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")


class PriceDataResponse(BaseModel):
    """Price data response model."""

    commodity: str = Field(..., description="Commodity symbol")
    data: List[PricePoint] = Field(..., description="OHLCV price data points")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "data": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "open": 2000.0,
                        "high": 2010.0,
                        "low": 1990.0,
                        "close": 2005.0,
                        "volume": 100000,
                    }
                ],
                "fetched_at": "2024-01-01T00:00:00Z",
            }
        }


class LatestPriceResponse(BaseModel):
    """Latest price response model."""

    commodity: str = Field(..., description="Commodity symbol")
    current_price: float = Field(..., description="Current price")
    change_24h: float = Field(..., description="24-hour price change percentage")
    change_24h_abs: float = Field(..., description="24-hour price change absolute")
    high_24h: Optional[float] = Field(None, description="24-hour high price")
    low_24h: Optional[float] = Field(None, description="24-hour low price")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "current_price": 2015.0,
                "change_24h": 0.5,
                "change_24h_abs": 10.05,
                "high_24h": 2020.0,
                "low_24h": 2000.0,
                "fetched_at": "2024-01-01T00:00:00Z",
            }
        }
