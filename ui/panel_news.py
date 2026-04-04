"""
ui/panel_news.py — Clean news cards, no emoji, no unicode arrows.
# TODO: Dev3 — add click-to-open-URL when real news items have links
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame, QHBoxLayout,
)
from PyQt6.QtCore import Qt

# sentiment → (left-border color, badge bg, badge text, badge text color)
_SENTIMENT = {
    "bullish": ("#4ADE80", "rgba(74,222,128,0.10)", "Bullish", "#4ADE80"),
    "bearish": ("#F87171", "rgba(248,113,113,0.10)", "Bearish", "#F87171"),
    "neutral": ("#6B7280", "rgba(107,114,128,0.10)", "Neutral", "#6B7280"),
}


class _NewsCard(QFrame):
    """Single news card with left sentiment accent strip."""

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)

        sentiment = item.get("sentiment", "neutral")
        bar_color, badge_bg, badge_text, badge_fg = _SENTIMENT.get(
            sentiment, _SENTIMENT["neutral"]
        )

        self.setObjectName("newsCard")
        self.setStyleSheet(f"""
            QFrame#newsCard {{
                background: #111111;
                border: 1px solid #1C1C1C;
                border-left: 2px solid {bar_color};
                border-radius: 8px;
            }}
            QFrame#newsCard:hover {{
                background: #141414;
                border-color: #262626;
                border-left-color: {bar_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 13)
        layout.setSpacing(5)

        # Row 1: sentiment badge + source + date
        top = QHBoxLayout()
        top.setSpacing(8)

        badge = QLabel(badge_text)
        badge.setFixedHeight(17)
        badge.setStyleSheet(
            f"background:{badge_bg}; color:{badge_fg};"
            "border-radius:4px; font-size:10px; font-weight:600;"
            "padding:0 8px; letter-spacing:0.3px;"
        )
        top.addWidget(badge)
        top.addStretch()

        source    = item.get("source", "")
        timestamp = item.get("timestamp", "")
        meta_text = f"{source}  {timestamp}" if source and timestamp else (source or timestamp)
        if meta_text:
            meta = QLabel(meta_text)
            meta.setStyleSheet("color:#374151; font-size:11px;")
            top.addWidget(meta)
        layout.addLayout(top)

        # Row 2: headline
        headline = item.get("title", item.get("headline", ""))
        if headline:
            lbl = QLabel(headline)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                "color:#F1F5F9; font-size:13px; font-weight:500; line-height:1.5;"
            )
            layout.addWidget(lbl)

        # Row 3: summary
        summary = item.get("summary", "")
        if summary:
            lbl2 = QLabel(summary)
            lbl2.setWordWrap(True)
            lbl2.setStyleSheet(
                "color:#6B7280; font-size:12px; line-height:1.5;"
            )
            layout.addWidget(lbl2)


class PanelNews(QWidget):
    """Scrollable news panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0D0D0D;")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("border:none; background:#0D0D0D;")

        self._content = QWidget()
        self._content.setStyleSheet("background:#0D0D0D;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, stretch=1)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #1C1C1C;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(18, 0, 18, 0)

        title = QLabel("News Feed")
        title.setStyleSheet(
            "color:#9CA3AF; font-size:12px; font-weight:500; letter-spacing:0.3px;"
        )
        row.addWidget(title)
        row.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color:#374151; font-size:11px;")
        row.addWidget(self._count_label)
        return bar

    def update_news(self, news_data: list[dict]) -> None:
        """
        Public contract: accepts dicts with keys
        headline|title, source, date|timestamp, sentiment, summary.
        """
        normalized = [
            {
                "title":     item.get("headline", item.get("title", "")),
                "source":    item.get("source", ""),
                "timestamp": item.get("date", item.get("timestamp", "")),
                "sentiment": item.get("sentiment", "neutral"),
                "summary":   item.get("summary", ""),
            }
            for item in news_data
        ]
        self.load_items(normalized)

    def load_items(self, items: list[dict]) -> None:
        while self._content_layout.count() > 1:
            it = self._content_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not items:
            ph = QLabel("No articles available.")
            ph.setStyleSheet("color:#374151; font-size:13px; padding:24px;")
            ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, ph)
            self._count_label.setText("")
            return

        for news_item in items:
            card = _NewsCard(news_item)
            self._content_layout.insertWidget(self._content_layout.count() - 1, card)

        n = len(items)
        self._count_label.setText(f"{n} article{'s' if n != 1 else ''}")
