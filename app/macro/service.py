"""Macro service module."""

from typing import List
from datetime import datetime, timezone

from app.macro.models import MacroNewsItem
from data.macro_insight_text import WORLD_MACRO_INSIGHT_TEXT
from src.data.services import news_service


class MacroService:
    """Macro service for world macro view endpoints."""

    async def get_macro_news(self) -> List[MacroNewsItem]:
        """Return global macro news for world view fetched from GDELT."""
        try:
            raw_items = news_service.fetch_real_world_news(limit=50)
        except Exception:
            raw_items = []
        return [
            MacroNewsItem(
                title=item.get("title", ""),
                source=item.get("source", ""),
                timestamp=item.get(
                    "timestamp",
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                ),
                sentiment=item.get("sentiment", "neutral"),
                summary=item.get("summary", ""),
            )
            for item in raw_items
        ]

    async def get_macro_insight(self) -> str:
        """Return a detailed mock global macroeconomic overview."""
        return WORLD_MACRO_INSIGHT_TEXT
