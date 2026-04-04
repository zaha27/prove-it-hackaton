"""Commodity model definitions."""

from enum import Enum

from pydantic import BaseModel, Field


class CommodityCategory(str, Enum):
    """Commodity categories."""

    ENERGY = "energy"
    METALS = "metals"
    AGRICULTURE = "agriculture"


class Commodity(BaseModel):
    """Commodity definition."""

    symbol: str = Field(..., description="Internal symbol (e.g., GOLD, OIL)")
    name: str = Field(..., description="Full name (e.g., Gold, Crude Oil)")
    category: CommodityCategory = Field(..., description="Commodity category")
    yfinance_symbol: str = Field(
        ..., description="YFinance symbol (e.g., GC=F, CL=F)"
    )
    description: str = Field(default="", description="Commodity description")

    class Config:
        frozen = True


# Predefined commodities
GOLD = Commodity(
    symbol="GOLD",
    name="Gold",
    category=CommodityCategory.METALS,
    yfinance_symbol="GC=F",
    description="Gold Futures - COMEX",
)

OIL = Commodity(
    symbol="OIL",
    name="Crude Oil (WTI)",
    category=CommodityCategory.ENERGY,
    yfinance_symbol="CL=F",
    description="West Texas Intermediate Crude Oil Futures - NYMEX",
)

COMMODITIES: dict[str, Commodity] = {
    "GOLD": GOLD,
    "OIL": OIL,
}
