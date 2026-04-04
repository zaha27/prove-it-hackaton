"""Change module Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Change24hResponse(BaseModel):
    """24-hour change response model."""

    commodity: str = Field(..., description="Commodity symbol")
    current_price: float = Field(..., description="Current price")
    change_24h: float = Field(..., description="24-hour price change percentage")
    change_24h_abs: float = Field(..., description="24-hour price change absolute")
    change_24h_direction: str = Field(
        ..., description="Change direction (up, down, neutral)"
    )
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
                "change_24h_direction": "up",
                "fetched_at": "2024-01-01T00:00:00Z",
            }
        }


class ChangeComparisonResponse(BaseModel):
    """Change comparison response model."""

    base_commodity: str = Field(..., description="Base commodity symbol")
    target_commodity: str = Field(..., description="Target commodity symbol")
    base_change_24h: float = Field(..., description="Base commodity 24h change %")
    target_change_24h: float = Field(..., description="Target commodity 24h change %")
    change_difference: float = Field(..., description="Difference in 24h change %")
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when data was fetched",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "base_commodity": "GOLD",
                "target_commodity": "SILVER",
                "base_change_24h": 0.5,
                "target_change_24h": 1.2,
                "change_difference": 0.7,
                "fetched_at": "2024-01-01T00:00:00Z",
            }
        }
