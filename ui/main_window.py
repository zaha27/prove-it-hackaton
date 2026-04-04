"""
ui/main_window.py — Main application window layout.
"""
import logging
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QVBoxLayout, QStatusBar,
)
from PyQt6.QtCore import Qt

from ui.sidebar import Sidebar
from ui.panel_news import PanelNews
from ui.panel_ai import PanelAI

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.

    Layout:
        ┌────────────┬───────────────────────────────────┐
        │            │         Chart Panel               │
        │  Sidebar   ├────────────────┬──────────────────┤
        │  (200px)   │  News Feed     │   AI Insight     │
        └────────────┴────────────────┴──────────────────┘
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Commodity Analyzer")
        self.resize(1400, 900)
        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        # Separator line
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background:#30363d;")
        root.addWidget(sep)

        # Main content area — will host chart + bottom panels
        self._main_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_splitter.setHandleWidth(2)

        # Chart placeholder — will be replaced by AppBridge
        self._chart_container = QWidget()
        self._chart_layout = QVBoxLayout(self._chart_container)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        self._main_splitter.addWidget(self._chart_container)

        # Bottom row: news + AI
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setHandleWidth(2)
        self.panel_news = PanelNews()
        self.panel_ai = PanelAI()
        bottom_splitter.addWidget(self.panel_news)
        bottom_splitter.addWidget(self.panel_ai)
        bottom_splitter.setSizes([500, 500])

        self._main_splitter.addWidget(bottom_splitter)
        self._main_splitter.setSizes([580, 320])

        root.addWidget(self._main_splitter, stretch=1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready — select a commodity")

    def set_chart_widget(self, widget: QWidget) -> None:
        """
        Inject any QWidget into the chart slot.

        HOW THE CHARTS DEV USES THIS:
        ─────────────────────────────
        # In main.py, after window = MainWindow():
        from charts.panel_chart import PanelChart
        panel_chart = PanelChart()          # has a QWebEngineView inside
        window.set_chart_widget(panel_chart)

        # Later, when data arrives:
        panel_chart.load_data(ohlcv_dict)   # re-renders the Plotly HTML

        The _chart_layout (QVBoxLayout) is the empty placeholder container.
        Calling set_chart_widget() clears whatever is there and inserts the new widget.
        """
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._chart_layout.addWidget(widget)

    # ── Public contract methods (called by Bridge / Backend) ──────────────────

    def update_news(self, items: list[dict]) -> None:
        """
        Feed news data to the news panel.
        Accepts both old keys (title/timestamp) and new keys (headline/date).
        """
        self.panel_news.update_news(items)

    def update_insight(self, text: str) -> None:
        """Feed AI insight text to the AI panel."""
        self.panel_ai.update_insight(text)

    def set_fetching(self, symbol: str) -> None:
        """
        Loading state ON — call this right after a signal fires (commodity_changed
        or timeframe_changed) and before the async fetch starts.

        HOW TO WIRE IN main.py / bridge.py:
            sidebar.commodity_changed.connect(window.set_fetching)
            panel_chart.timeframe_changed.connect(
                lambda tf: window.set_fetching(window._current_symbol or tf)
            )
        """
        self._status_bar.showMessage(f"  {symbol}  |  Fetching data...")
        self.panel_ai.set_loading(True)

    def set_loading(self, loading: bool) -> None:
        """Toggle loading state on the AI panel (used by bridge.py)."""
        self.panel_ai.set_loading(loading)

    def update_status(self, symbol: str, price: float | None) -> None:
        """Update status bar with current symbol and price."""
        ts = datetime.now().strftime("%H:%M:%S")
        if price is not None:
            self._status_bar.showMessage(
                f"  {symbol}  |  {price:,.3f}  |  Last updated: {ts}"
            )
        else:
            self._status_bar.showMessage(f"  {symbol}  |  —  |  {ts}")
