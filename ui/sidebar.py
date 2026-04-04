"""
ui/sidebar.py — Sidebar with commodity list and refresh button.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel,
)
from PyQt6.QtCore import pyqtSignal, Qt

from config import SYMBOLS


class Sidebar(QWidget):
    """
    Left sidebar widget.

    Signals:
        commodity_selected(str): emits the ticker symbol when user clicks a commodity.
        refresh_clicked(): emits when the Refresh button is pressed.
    """

    # Primary signal — use this one to connect in main.py / bridge.py
    commodity_changed = pyqtSignal(str)   # emits ticker, e.g. "GC=F"
    # Kept for backwards-compatibility with bridge.py
    commodity_selected = pyqtSignal(str)
    refresh_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._symbol_map: dict[str, str] = {}  # display name → ticker
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        title = QLabel("⬡ COMMODITIES")
        title.setStyleSheet(
            "color:#FFD700;font-size:11px;font-weight:bold;letter-spacing:2px;"
        )
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setSpacing(2)
        for ticker, name in SYMBOLS.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            self._list.addItem(item)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, stretch=1)

        self._refresh_btn = QPushButton("↺  Refresh")
        self._refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self._refresh_btn)

    def _on_selection_changed(self, current: QListWidgetItem, _prev) -> None:
        if current:
            ticker = current.data(Qt.ItemDataRole.UserRole)
            self.commodity_changed.emit(ticker)   # ← connect to this
            self.commodity_selected.emit(ticker)  # ← bridge.py uses this

    def select_first(self) -> None:
        """Programmatically select the first commodity in the list."""
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
