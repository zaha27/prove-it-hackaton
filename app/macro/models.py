"""Macro module Pydantic models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MacroSentiment(str, Enum):
    """Allowed sentiment values for macro news."""

    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class MacroNewsItem(BaseModel):
    """Single global macro news item."""

    title: str = Field(..., description="News title")
    source: str = Field(..., description="News source")
    timestamp: datetime = Field(..., description="Publication timestamp")
    sentiment: MacroSentiment = Field(..., description="Sentiment label")
    summary: str = Field(..., description="Short summary")


class MacroInsightResponse(BaseModel):
    """Global macro insight response."""

    insight: str = Field(..., description="Global macroeconomic overview")
