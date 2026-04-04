"""
bridge.py — AppBridge: connects UI events to data layer via QThread.

Data flow:
    UI signal → AppBridge → _FetchWorker (QThread)
                            ├── backend_client (FastAPI on :8000)  [primary]
                            └── data/market + data/ai_engine       [fallback if backend down]
"""
import logging

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer

logger = logging.getLogger(__name__)

LIVE_REFRESH_INTERVAL_MS = 600_000   # 10 minutes
DEFAULT_RANGE    = "1Y"
DEFAULT_INTERVAL = "1D"


class _FetchWorker(QThread):
    """Background thread — fetches price, news, AI insight without blocking UI."""

    data_ready    = pyqtSignal(dict, list, dict)   # (price_data, news, consensus_result)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        symbol: str,
        range_str: str = DEFAULT_RANGE,
        interval_str: str = DEFAULT_INTERVAL,
        include_context: bool = True,
        use_consensus: bool = True,  # New: use DeepSeek-Gemma4 consensus
        parent=None,
    ):
        super().__init__(parent)
        self.symbol          = symbol
        self.range_str       = range_str
        self.interval_str    = interval_str
        self.include_context = include_context
        self.use_consensus   = use_consensus
        self._cancelled      = False

    def cancel(self) -> None:
        """Signal the worker to cancel ongoing operations."""
        self._cancelled = True
        logger.info("Worker cancelled for %s", self.symbol)

    def is_cancelled(self) -> bool:
        """Check if worker has been cancelled."""
        return self._cancelled

    def run(self) -> None:
        try:
            from data import backend_client

            if backend_client.is_backend_available():
                logger.info("Using backend API for %s", self.symbol)
                price_data = backend_client.get_price_data(
                    self.symbol, self.range_str, self.interval_str
                ) or {}
                if self.include_context:
                    news    = backend_client.get_news(self.symbol)

                    # Use new consensus endpoint if enabled
                    if self.use_consensus:
                        consensus_result = backend_client.get_consensus(self.symbol)
                    else:
                        consensus_result = None
                else:
                    news, consensus_result = [], None
            else:
                # Backend not running — use yfinance + DeepSeek directly
                logger.warning("Backend unavailable — using direct APIs for %s", self.symbol)
                from data import market, news as news_module, ai_engine
                price_data = market.get_price_data(
                    self.symbol,
                    range_str=self.range_str,
                    interval_str=self.interval_str,
                ) or {}
                if self.include_context:
                    news    = news_module.get_news(self.symbol)
                    # Fallback to old insight method
                    insight_text = ai_engine.get_ai_insight(self.symbol, price_data, news)
                    consensus_result = {"final_recommendation": insight_text, "fallback": True}
                else:
                    news, consensus_result = [], None

            self.data_ready.emit(price_data or {}, news, consensus_result or {})

        except Exception as exc:
            logger.error("FetchWorker error for %s: %s", self.symbol, exc)
            self.error_occurred.emit(str(exc))


class AppBridge(QObject):
    """Mediator between the UI (MainWindow, PanelChart) and the data layer."""

    def __init__(self, main_window, panel_chart):
        super().__init__()
        self._window          = main_window
        self._panel_chart     = panel_chart
        self._worker: _FetchWorker | None = None
        self._current_range    = DEFAULT_RANGE
        self._current_interval = DEFAULT_INTERVAL
        self._current_symbol: str | None = None

        # Connect sidebar signals
        self._window.sidebar.commodity_selected.connect(self.on_select)
        self._window.sidebar.refresh_clicked.connect(self._on_refresh)

        # Connect chart timeframe changes
        self._panel_chart.timeframe_changed.connect(self._on_timeframe_changed)

        # Live refresh every 10 minutes
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(LIVE_REFRESH_INTERVAL_MS)
        self._live_timer.timeout.connect(self._on_live_tick)
        self._live_timer.start()

    # ── Public ─────────────────────────────────────────────────────────────────

    def on_select(self, symbol: str) -> None:
        self._current_symbol = symbol
        self._fetch(symbol)

    # ── Private ────────────────────────────────────────────────────────────────

    def _on_refresh(self) -> None:
        if self._current_symbol:
            self._fetch(self._current_symbol, include_context=True)

    def _on_timeframe_changed(self, range_val: str, interval_val: str) -> None:
        self._current_range = range_val if range_val in {"6M", "1Y", "5Y", "Max"} else DEFAULT_RANGE
        self._current_interval = interval_val if interval_val in {"1D", "1W", "1M"} else DEFAULT_INTERVAL
        if self._current_symbol:
            self._fetch(self._current_symbol)

    def _on_live_tick(self) -> None:
        if self._current_symbol:
            self._fetch(self._current_symbol, include_context=False)

    def _fetch(self, symbol: str, include_context: bool = True) -> None:
        # Cancel any ongoing worker immediately
        if self._worker and self._worker.isRunning():
            logger.info("Cancelling previous fetch for %s", self._worker.symbol)
            self._worker.cancel()  # Signal cancellation
            self._worker.quit()
            self._worker.wait(100)  # Short wait, don't block UI
            self._worker = None

        self._window.set_loading(True)
        self._window.update_status(symbol, None)
        # Show animated loading in AI panel
        self._window.show_ai_loading(symbol)

        self._worker = _FetchWorker(
            symbol,
            range_str=self._current_range,
            interval_str=self._current_interval,
            include_context=include_context,
        )
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_data_ready(self, price_data: dict, news: list, consensus_result: dict) -> None:
        symbol = price_data.get("symbol", self._current_symbol or "")

        if price_data and price_data.get("close"):
            self._panel_chart.load_data(price_data)
            last_price = price_data["close"][-1] if price_data["close"] else None
        else:
            self._panel_chart.show_placeholder()
            last_price = None

        if news:
            self._window.update_news(news)

        # Handle consensus result (new format) or fallback insight string
        if consensus_result:
            if consensus_result.get("fallback"):
                # Old format - just a text insight
                self._window.update_insight(consensus_result.get("final_recommendation", ""))
            else:
                # New consensus format with debate history
                self._window.update_consensus(consensus_result)

        self._window.set_loading(False)
        self._window.update_status(symbol, last_price)

    def _on_error(self, message: str) -> None:
        logger.error("Fetch failed: %s", message)
        self._window.set_loading(False)
        self._window.update_insight(f"Data fetch failed:\n\n{message}")
