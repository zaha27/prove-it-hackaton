"""
bridge.py — AppBridge: connects UI events to data layer via QThread.

Data flow:
    UI signal → AppBridge → _FetchWorker (QThread)
                            ├── backend_client (FastAPI on :8000)  [primary]
                            └── data/market + data/ai_engine       [fallback if backend down]
"""
import logging
import os

import requests
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer

logger = logging.getLogger(__name__)

LIVE_REFRESH_INTERVAL_MS = 600_000   # 10 minutes
DEFAULT_RANGE    = "1Y"
DEFAULT_INTERVAL = "1D"
MACRO_BASE_URL   = os.getenv("BACKEND_URL", "http://localhost:8000")
MACRO_TIMEOUT_S  = 12


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

    @staticmethod
    def _is_consensus_invalid(consensus_result: dict | None) -> bool:
        """Return True if consensus payload is missing or represents a failed run."""
        if not consensus_result:
            return True
        return (
            not consensus_result.get("consensus_reached", False)
            and consensus_result.get("rounds_conducted", 0) == 0
        )

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
                        # Fallback to fast insight if consensus is unavailable/errored
                        if self._is_consensus_invalid(consensus_result):
                            insight_text = backend_client.get_ai_insight(
                                self.symbol, price_data, news
                            )
                            consensus_result = {
                                "final_recommendation": insight_text,
                                "fallback": True,
                            }
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


class _MacroFetchWorker(QThread):
    """Background thread — fetches macro news and macro insight from FastAPI backend."""

    macro_data_ready = pyqtSignal(list, str)  # (news, insight)
    error_occurred = pyqtSignal(str)

    def run(self) -> None:
        try:
            news_resp = requests.get(
                f"{MACRO_BASE_URL}/macro/news",
                timeout=MACRO_TIMEOUT_S,
            )
            news_resp.raise_for_status()
            news_payload = news_resp.json()
            if isinstance(news_payload, list):
                news_items = news_payload
            elif isinstance(news_payload, dict):
                news_items = (
                    news_payload.get("news")
                    or news_payload.get("items")
                    or news_payload.get("articles")
                    or []
                )
            else:
                news_items = []

            insight_resp = requests.get(
                f"{MACRO_BASE_URL}/macro/insight",
                timeout=MACRO_TIMEOUT_S,
            )
            insight_resp.raise_for_status()
            insight_payload = insight_resp.json()
            if isinstance(insight_payload, str):
                insight_text = insight_payload
            elif isinstance(insight_payload, dict):
                insight_text = (
                    insight_payload.get("insight")
                    or insight_payload.get("text")
                    or insight_payload.get("content")
                    or ""
                )
            else:
                insight_text = ""

            self.macro_data_ready.emit(news_items, insight_text)

        except requests.exceptions.ConnectionError:
            self.error_occurred.emit(
                f"Macro data unavailable: cannot connect to backend at {MACRO_BASE_URL}."
            )
        except requests.exceptions.Timeout:
            self.error_occurred.emit(
                "Macro data request timed out. Please try again in a few moments."
            )
        except requests.exceptions.RequestException as exc:
            self.error_occurred.emit(f"Macro data request failed: {exc}")
        except Exception as exc:
            self.error_occurred.emit(f"Unexpected macro data error: {exc}")


class AppBridge(QObject):
    """Mediator between the UI (MainWindow, PanelChart) and the data layer."""

    def __init__(self, main_window, panel_chart):
        super().__init__()
        self._window          = main_window
        self._panel_chart     = panel_chart
        self._worker: _FetchWorker | None = None
        self._macro_worker: _MacroFetchWorker | None = None
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

        # Load macro view data once on app startup.
        self.fetch_macro_data()

    # ── Public ─────────────────────────────────────────────────────────────────

    def on_select(self, symbol: str) -> None:
        self._current_symbol = symbol
        self._fetch(symbol)

    def fetch_macro_data(self) -> None:
        if self._macro_worker and self._macro_worker.isRunning():
            self._macro_worker.quit()
            self._macro_worker.wait(100)
            self._macro_worker = None

        self._set_macro_loading(True)

        self._macro_worker = _MacroFetchWorker()
        self._macro_worker.macro_data_ready.connect(self._on_macro_data_ready)
        self._macro_worker.error_occurred.connect(self._on_macro_error)
        self._macro_worker.start()

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

    def _on_macro_data_ready(self, news: list, insight: str) -> None:
        self._window.update_macro_news(news)
        self._window.update_macro_insight(insight)
        self._set_macro_loading(False)

    def _on_macro_error(self, message: str) -> None:
        logger.error("Macro fetch failed: %s", message)
        self._window.update_macro_news([])
        self._window.update_macro_insight(f"Macro data fetch failed:\n\n{message}")
        self._set_macro_loading(False)

    def _set_macro_loading(self, is_loading: bool) -> None:
        if hasattr(self._window, "macro_ai"):
            self._window.macro_ai.set_loading(is_loading)
        elif hasattr(self._window, "panel_ai"):
            self._window.panel_ai.set_loading(is_loading)
