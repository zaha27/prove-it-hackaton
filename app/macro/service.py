"""Macro service module."""

from typing import List

from app.macro.models import MacroNewsItem
from data.macro_insight_text import WORLD_MACRO_INSIGHT_TEXT
from data.news import fetch_real_world_news


class MacroService:
    """Macro service for world macro view endpoints."""

    async def get_macro_news(self) -> List[MacroNewsItem]:
        """Return global macro news for world view fetched from GDELT."""
        raw_items = fetch_real_world_news(limit=50)
        return [
            MacroNewsItem(
                title=item.get("title", ""),
                source=item.get("source", ""),
                timestamp=item.get("timestamp", "1970-01-01T00:00:00Z"),
                sentiment=item.get("sentiment", "neutral"),
                summary=item.get("summary", ""),
            )
            for item in raw_items
        ]

    async def get_macro_insight(self) -> str:
        """Return a detailed mock global macroeconomic overview."""
        return WORLD_MACRO_INSIGHT_TEXT
