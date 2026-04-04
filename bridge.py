"""
bridge.py — AppBridge: connects UI events to data layer via QThread.
"""
import logging

from PyQt6.QtCore import QThread, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class _FetchWorker(QThread):
    """
    Background thread that fetches price data, news, and AI insight
    without blocking the UI event loop.
    """

    data_ready = pyqtSignal(dict, list, str)   # (price_data, news, insight)
    error_occurred = pyqtSignal(str)

    def __init__(self, symbol: str, use_mock: bool = False, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.use_mock = use_mock

    def run(self) -> None:
        try:
            if self.use_mock:
                from data import mock_data
                price_data = mock_data.get_price_data(self.symbol)
                news = mock_data.get_news(self.symbol)
                insight = mock_data.get_ai_insight(self.symbol)
            else:
                from data import market, news as news_module, ai_engine
                price_data = market.get_price_data(self.symbol) or {}
                news = news_module.get_news(self.symbol)
                insight = ai_engine.get_ai_insight(self.symbol, price_data, news)

            self.data_ready.emit(price_data, news, insight)

        except Exception as exc:
            logger.error("FetchWorker error for %s: %s", self.symbol, exc)
            self.error_occurred.emit(str(exc))


class AppBridge(QObject):
    """
    Mediator between the UI (MainWindow, PanelChart) and the data layer.

    Handles async data loading via QThread so the GUI stays responsive.
    """

    def __init__(self, main_window, panel_chart, use_mock: bool = False):
        super().__init__()
        self._window = main_window
        self._panel_chart = panel_chart
        self._use_mock = use_mock
        self._worker: _FetchWorker | None = None

        # Connect sidebar signals
        self._window.sidebar.commodity_selected.connect(self.on_select)
        self._window.sidebar.refresh_clicked.connect(self._on_refresh)

        # Connect chart timeframe changes
        self._panel_chart.timeframe_changed.connect(self._on_timeframe_changed)

        self._current_symbol: str | None = None

    def on_select(self, symbol: str) -> None:
        """Called when the user selects a commodity from the sidebar."""
        self._current_symbol = symbol
        self._fetch(symbol)

    def _on_refresh(self) -> None:
        """Re-fetch data for the currently selected symbol."""
        if self._current_symbol:
            self._fetch(self._current_symbol)

    def _on_timeframe_changed(self, timeframe: str) -> None:
        """
        Re-fetch when timeframe changes.
        # TODO: Dev2 — pass timeframe to market.get_price_data(symbol, period_days=...)
        """
        logger.info("Timeframe changed to %s (re-fetch not yet wired)", timeframe)
        if self._current_symbol:
            self._fetch(self._current_symbol)

    def _fetch(self, symbol: str) -> None:
        """Start background fetch. Cancels any in-progress worker."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(500)

        self._window.set_loading(True)
        self._window.update_status(symbol, None)

        self._worker = _FetchWorker(symbol, use_mock=self._use_mock)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_data_ready(self, price_data: dict, news: list, insight: str) -> None:
        symbol = price_data.get("symbol", self._current_symbol or "")

        # Update chart
        if price_data and price_data.get("close"):
            self._panel_chart.load_data(price_data)
            last_price = price_data["close"][-1] if price_data["close"] else None
        else:
            self._panel_chart.show_placeholder()
            last_price = None

        # Update panels
        self._window.update_news(news)
        self._window.update_insight(insight)
        self._window.set_loading(False)
        self._window.update_status(symbol, last_price)

    def _on_error(self, message: str) -> None:
        logger.error("Fetch failed: %s", message)
        self._window.set_loading(False)
        self._window.update_insight(f"Data fetch failed:\n\n{message}")
