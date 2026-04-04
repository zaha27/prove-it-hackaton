"""
ui/sidebar.py — Clean Perplexity-style sidebar, no emoji, no unicode symbols.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from config import SYMBOLS


class Sidebar(QWidget):
    commodity_changed  = pyqtSignal(str)  # primary — connect here
    commodity_selected = pyqtSignal(str)  # compat — bridge.py uses this
    refresh_clicked    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(
            "background:#0D0D0D;"
            "border-right:1px solid #1C1C1C;"
        )
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_logo())
        layout.addWidget(self._build_section_label("Markets"))
        layout.addWidget(self._build_list(), stretch=1)
        layout.addWidget(self._build_bottom())

    def _build_logo(self) -> QWidget:
        """App identity block — top of sidebar."""
        container = QWidget()
        container.setFixedHeight(64)
        container.setStyleSheet(
            "background:#080808;"
            "border-bottom:1px solid #1C1C1C;"
        )
        row = QHBoxLayout(container)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(10)

        # Wordmark badge: "AI" in a small pill
        badge = QLabel("AI")
        badge.setFixedSize(32, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            "background:#1E3A5F;"
            "color:#93C5FD;"
            "border-radius:4px;"
            "font-size:11px;"
            "font-weight:700;"
            "letter-spacing:1px;"
        )
        row.addWidget(badge)

        # App name block
        name_block = QVBoxLayout()
        name_block.setSpacing(1)

        top_line = QLabel("Commodity")
        top_line.setStyleSheet(
            "color:#F1F5F9;"
            "font-size:13px;"
            "font-weight:600;"
            "letter-spacing:0.2px;"
        )
        bot_line = QLabel("Analyzer")
        bot_line.setStyleSheet(
            "color:#374151;"
            "font-size:11px;"
            "font-weight:400;"
            "letter-spacing:0.5px;"
        )
        name_block.addWidget(top_line)
        name_block.addWidget(bot_line)
        row.addLayout(name_block)
        row.addStretch()
        return container

    def _build_section_label(self, text: str) -> QWidget:
        lbl = QLabel(text.upper())
        lbl.setFixedHeight(32)
        lbl.setContentsMargins(22, 10, 0, 0)
        lbl.setStyleSheet(
            "color:#374151;"
            "font-size:10px;"
            "font-weight:600;"
            "letter-spacing:1.2px;"
        )
        return lbl

    def _build_list(self) -> QListWidget:
        self._list = QListWidget()
        self._list.setSpacing(0)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setStyleSheet(
            "QListWidget { background:transparent; border:none; outline:none; }"
            "QListWidget::item {"
            "  padding:9px 16px;"
            "  color:#6B7280;"
            "  border-radius:6px;"
            "  margin:1px 6px;"
            "  font-size:13px;"
            "}"
            "QListWidget::item:hover { background:#111111; color:#D1D5DB; }"
            "QListWidget::item:selected {"
            "  background:#111111;"
            "  color:#93C5FD;"
            "  border-left:2px solid #93C5FD;"
            "  padding-left:14px;"
            "  font-weight:500;"
            "}"
        )
        for ticker, name in SYMBOLS.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            item.setToolTip(ticker)
            self._list.addItem(item)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        return self._list

    def _build_bottom(self) -> QWidget:
        container = QWidget()
        container.setFixedHeight(60)
        container.setStyleSheet(
            "background:#080808;"
            "border-top:1px solid #1C1C1C;"
        )
        row = QHBoxLayout(container)
        row.setContentsMargins(12, 10, 12, 10)

        btn = QPushButton("Refresh")
        btn.setFixedHeight(32)
        btn.setStyleSheet(
            "QPushButton {"
            "  background:#111111; color:#6B7280;"
            "  border:1px solid #1C1C1C; border-radius:6px;"
            "  font-size:12px; font-weight:500;"
            "}"
            "QPushButton:hover {"
            "  background:#1C1C1C; color:#93C5FD;"
            "  border-color:#93C5FD;"
            "}"
            "QPushButton:pressed { background:#1E3A5F; color:#93C5FD; }"
        )
        btn.clicked.connect(self.refresh_clicked.emit)
        self._refresh_btn = btn
        row.addWidget(btn)
        return container

    def _on_selection_changed(self, current: QListWidgetItem, _prev) -> None:
        if current:
            ticker = current.data(Qt.ItemDataRole.UserRole)
            self.commodity_changed.emit(ticker)
            self.commodity_selected.emit(ticker)

    def select_first(self) -> None:
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
