"""Macro module Pydantic models."""

from pydantic import BaseModel, Field


class MacroNewsItem(BaseModel):
    """Single global macro news item."""

    title: str = Field(..., description="News title")
    source: str = Field(..., description="News source")
    timestamp: str = Field(..., description="Publication timestamp")
    sentiment: str = Field(..., description="Sentiment label")
    summary: str = Field(..., description="Short summary")


class MacroInsightResponse(BaseModel):
    """Global macro insight response."""

    insight: str = Field(..., description="Global macroeconomic overview")

