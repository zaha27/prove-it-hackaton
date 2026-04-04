"""
ui/panel_news.py — Scrollable news feed panel with sentiment badges.
# TODO: Dev3 — add click-to-open-URL when real news items have links
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame, QHBoxLayout,
)
from PyQt6.QtCore import Qt

_SENTIMENT_COLORS = {
    "bullish": ("#1a472a", "#26a69a", "▲ BULLISH"),
    "bearish": ("#4a1414", "#ef5350", "▼ BEARISH"),
    "neutral": ("#1c2128", "#8b949e", "◆ NEUTRAL"),
}


class _NewsCard(QFrame):
    """Single news item card."""

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame{background:#161b22;border:1px solid #30363d;border-radius:6px;"
            "margin:2px 0;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header row: sentiment badge + source + timestamp
        header = QHBoxLayout()
        sentiment = item.get("sentiment", "neutral")
        bg, fg, label = _SENTIMENT_COLORS.get(sentiment, _SENTIMENT_COLORS["neutral"])
        badge = QLabel(label)
        badge.setStyleSheet(
            f"background:{bg};color:{fg};border:1px solid {fg};border-radius:3px;"
            "font-size:10px;font-weight:bold;padding:1px 6px;"
        )
        badge.setFixedHeight(18)
        header.addWidget(badge)
        header.addStretch()
        meta = QLabel(f"{item.get('source', '')}  ·  {item.get('timestamp', '')}")
        meta.setStyleSheet("color:#8b949e;font-size:11px;")
        header.addWidget(meta)
        layout.addLayout(header)

        # Title
        title = QLabel(item.get("title", ""))
        title.setWordWrap(True)
        title.setStyleSheet("color:#e6edf3;font-weight:bold;font-size:13px;")
        layout.addWidget(title)

        # Summary
        if item.get("summary"):
            summary = QLabel(item["summary"])
            summary.setWordWrap(True)
            summary.setStyleSheet("color:#8b949e;font-size:12px;")
            layout.addWidget(summary)


class PanelNews(QWidget):
    """
    News panel — a scrollable list of news cards with sentiment badges.

    Usage:
        panel.load_items(list_of_news_dicts)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("  NEWS FEED")
        header.setFixedHeight(32)
        header.setStyleSheet(
            "background:#161b22;color:#FFD700;font-size:11px;font-weight:bold;"
            "letter-spacing:2px;border-bottom:1px solid #30363d;padding-left:8px;"
        )
        layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, stretch=1)

    def load_items(self, items: list[dict]) -> None:
        """Replace current news cards with new items."""
        # Clear existing cards (keep the trailing stretch)
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for news_item in items:
            card = _NewsCard(news_item)
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, card
            )

        if not items:
            placeholder = QLabel("No news available.")
            placeholder.setStyleSheet("color:#8b949e;padding:20px;")
            self._content_layout.insertWidget(0, placeholder)
