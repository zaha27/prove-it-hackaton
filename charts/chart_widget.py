"""
charts/chart_widget.py — QWebEngineView wrapper for Plotly charts.
"""
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

from charts.chart_engine import build_candlestick, PLACEHOLDER_HTML

logger = logging.getLogger(__name__)


class ChartWidget(QWidget):
    """
    Widget that hosts a QWebEngineView and renders Plotly HTML charts.

    Usage:
        widget = ChartWidget()
        widget.load_data(ohlcv_dict)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_ohlcv: dict | None = None
        self._current_indicator: str = "none"
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._web_view = QWebEngineView()
        self._web_view.setHtml(PLACEHOLDER_HTML)
        layout.addWidget(self._web_view)

    def load_data(self, ohlcv: dict) -> None:
        """Render candlestick chart from OHLCV data dict."""
        self._current_ohlcv = ohlcv
        self._render()

    def set_indicator(self, name: str) -> None:
        """Re-render chart with the selected indicator overlay."""
        self._current_indicator = name
        if self._current_ohlcv:
            self._render()

    def _render(self) -> None:
        if not self._current_ohlcv:
            return
        try:
            html = build_candlestick(self._current_ohlcv, indicator=self._current_indicator)
            self._web_view.setHtml(html)
        except Exception as exc:
            logger.error("ChartWidget render failed: %s", exc)

    def show_placeholder(self) -> None:
        """Reset chart to the initial placeholder."""
        self._current_ohlcv = None
        self._web_view.setHtml(PLACEHOLDER_HTML)
