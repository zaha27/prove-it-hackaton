"""
ui/main_window.py

Tab 0 — World Macro View:
    QHBoxLayout: left 30% (macro_news / macro_ai stacked) | right 70% (map_container)

Tab 1 — Trading Desk:
    Header row 1: "AI Commodity Analyzer" centrat
    Header row 2: commodity name + pret, stanga
    Body: sidebar (220px) | QSplitter(V): chart_container / panel_news + panel_ai

Loading API:
    window.show_loading(True,  "Fetching data...")
    window.show_loading(False)
"""
import logging
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QVBoxLayout, QStatusBar, QLabel, QTabWidget, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QMovie

from ui.sidebar import Sidebar
from ui.panel_news import PanelNews
from ui.panel_ai import PanelAI

logger = logging.getLogger(__name__)


# ── Spinner overlay ────────────────────────────────────────────────────────────

class _SpinnerOverlay(QWidget):
    """
    Overlay cu spinner GIF animat + mesaj.
    Pluteste deasupra parent-ului si se redimensioneaza automat via eventFilter.

    Daca spinner.gif lipseste, fallback la animatie text (puncte).
    """

    _GIF_PATH = os.path.join(os.path.dirname(__file__), "..", "spinner.gif")

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        parent.installEventFilter(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: rgba(8, 8, 8, 0.88);")
        self.hide()

        self._movie: QMovie | None = None
        self._fallback_count = 0
        self._fallback_timer = QTimer(self)
        self._fallback_timer.timeout.connect(self._tick_fallback)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        # Spinner (GIF via QMovie, sau un label text ca fallback)
        self._spinner_label = QLabel()
        self._spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spinner_label.setStyleSheet("background: transparent;")

        gif = os.path.abspath(self._GIF_PATH)
        if os.path.exists(gif):
            self._movie = QMovie(gif)
            self._spinner_label.setMovie(self._movie)
        else:
            # Fallback: patrat colorat animat ca pseudo-spinner
            self._spinner_label.setFixedSize(32, 32)
            self._spinner_label.setStyleSheet(
                "background: #1E3A5F; border-radius: 6px;"
            )

        layout.addWidget(self._spinner_label)

        # Mesaj
        self._msg_label = QLabel("Fetching data...")
        self._msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_label.setStyleSheet(
            "color: #93C5FD;"
            "font-size: 13px;"
            "font-weight: 500;"
            "letter-spacing: 0.3px;"
            "background: transparent;"
        )
        layout.addWidget(self._msg_label)

    # ── Public ─────────────────────────────────────────────────────────────────

    def show_loading(self, message: str = "Fetching data...") -> None:
        self._msg_label.setText(message)
        self.resize(self.parent().size())
        self.raise_()
        self.show()
        if self._movie:
            self._movie.start()
        else:
            self._fallback_count = 0
            self._fallback_timer.start(350)

    def hide_loading(self) -> None:
        if self._movie:
            self._movie.stop()
        self._fallback_timer.stop()
        self.hide()

    # ── Internals ──────────────────────────────────────────────────────────────

    def _tick_fallback(self) -> None:
        """Fallback cand GIF-ul lipseste: animeaza mesajul cu puncte."""
        self._fallback_count = (self._fallback_count + 1) % 4
        base = self._msg_label.text().rstrip(".")
        self._msg_label.setText(base + "." * self._fallback_count)

    def eventFilter(self, source, event) -> bool:
        if source is self.parent() and event.type() == QEvent.Type.Resize:
            self.resize(source.size())
        return super().eventFilter(source, event)


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    Layout global:

    QVBoxLayout (central widget)
    ├── QTabWidget
    │   ├── Tab 0: World Macro View
    │   │    QHBoxLayout
    │   │    ├── Left 30%: QSplitter(V)  macro_news / macro_ai
    │   │    └── Right 70%: map_container  [+ _map_overlay]
    │   │
    │   └── Tab 1: Trading Desk
    │        QVBoxLayout
    │        ├── Header row 1: titlu app centrat
    │        ├── Header row 2: commodity name + pret, stanga
    │        └── QHBoxLayout
    │             ├── Sidebar (220px)
    │             └── QSplitter(V)
    │                  ├── chart_container  [+ _chart_overlay]
    │                  └── QSplitter(H): panel_news / panel_ai
    │
    └── Status bar
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Commodity AI Analyzer")
        self.resize(1440, 900)
        self.setStyleSheet("background: #080808;")
        self._current_symbol: str = ""
        self._map_placeholder: QLabel | None = None
        self._init_ui()

    # ── Construction ───────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet("background: #080808;")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_tabs(), stretch=1)

        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar {"
            "  background: #080808; color: #374151;"
            "  border-top: 1px solid #111111;"
            "  font-size: 11px; padding: 0 14px;"
            "}"
        )
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Select a commodity to load data")

    def _build_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_tab_macro(),   "World Macro View")
        self._tabs.addTab(self._build_tab_trading(), "Trading Desk")
        return self._tabs

    # ── Tab 0: World Macro View ────────────────────────────────────────────────

    def _build_tab_macro(self) -> QWidget:
        """
        QHBoxLayout
        ├── Left  30%: QSplitter(V)  macro_news (sus) / macro_ai (jos)
        └── Right 70%: map_container  [+ _map_overlay flotant deasupra]

        Colegul injecteaza harta cu:
            window.set_map_widget(web_view)
        """
        tab = QWidget()
        tab.setStyleSheet("background: #080808;")

        outer = QHBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(1)

        # Stanga 30%: macro panels stacked
        left_split = QSplitter(Qt.Orientation.Vertical)
        left_split.setHandleWidth(1)
        self.macro_news = PanelNews()
        self.macro_ai   = PanelAI()
        left_split.addWidget(self.macro_news)
        left_split.addWidget(self.macro_ai)
        left_split.setSizes([450, 450])
        h_splitter.addWidget(left_split)

        # Dreapta 70%: map container + overlay
        self.map_container = QFrame()
        self.map_container.setFrameShape(QFrame.Shape.NoFrame)
        self.map_container.setStyleSheet("background: #080808;")
        self._map_layout = QVBoxLayout(self.map_container)
        self._map_layout.setContentsMargins(0, 0, 0, 0)

        self._map_placeholder = QLabel("World map will appear here")
        self._map_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._map_placeholder.setStyleSheet("color: #374151; font-size: 13px;")
        self._map_layout.addWidget(self._map_placeholder)

        self._map_overlay = _SpinnerOverlay(self.map_container)
        h_splitter.addWidget(self.map_container)

        # 30 / 70 proportional split
        h_splitter.setSizes([432, 1008])

        outer.addWidget(h_splitter)
        return tab

    # ── Tab 1: Trading Desk ────────────────────────────────────────────────────

    def _build_tab_trading(self) -> QWidget:
        """
        QVBoxLayout
        ├── _build_trading_header()   (doua randuri: titlu + commodity/pret)
        └── QHBoxLayout
             ├── Sidebar (220px)
             └── QSplitter(V)
                  ├── chart_container  [+ _chart_overlay]
                  └── QSplitter(H): panel_news / panel_ai

        Colegul injecteaza graficul cu:
            window.set_chart_widget(panel_chart)
        """
        tab = QWidget()
        tab.setStyleSheet("background: #080808;")

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        tab_layout.addWidget(self._build_trading_header())

        # Body
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = Sidebar()
        body.addWidget(self.sidebar)

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(1)

        self._chart_container = QWidget()
        self._chart_container.setStyleSheet("background: #080808;")
        self._chart_layout = QVBoxLayout(self._chart_container)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        self._chart_overlay = _SpinnerOverlay(self._chart_container)
        v_splitter.addWidget(self._chart_container)

        bottom = QSplitter(Qt.Orientation.Horizontal)
        bottom.setHandleWidth(1)
        self.panel_news = PanelNews()
        self.panel_ai   = PanelAI()
        bottom.addWidget(self.panel_news)
        bottom.addWidget(self.panel_ai)
        bottom.setSizes([520, 520])
        v_splitter.addWidget(bottom)
        v_splitter.setSizes([570, 330])

        body.addWidget(v_splitter, stretch=1)
        tab_layout.addLayout(body, stretch=1)
        return tab

    def _build_trading_header(self) -> QWidget:
        """
        Doua randuri vizuale deasupra chart-ului in Trading Desk:

        Rand 1 (inalt 38px): "AI Commodity Analyzer"  —  centrat, font bold 17px
        Rand 2 (inalt 30px): [Commodity name]  [Pret]  [dot]  —  stanga
        """
        container = QWidget()
        container.setStyleSheet(
            "background: #080808;"
            "border-bottom: 1px solid #1C1C1C;"
        )
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Rand 1 — titlu app centrat
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_row = QHBoxLayout(title_bar)
        title_row.setContentsMargins(0, 0, 0, 0)

        app_title = QLabel("AI Commodity Analyzer")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_title.setStyleSheet(
            "color: #F1F5F9;"
            "font-size: 17px;"
            "font-weight: 700;"
            "letter-spacing: 0.2px;"
        )
        title_row.addWidget(app_title)
        vbox.addWidget(title_bar)

        # Rand 2 — commodity name + pret, stanga
        info_bar = QWidget()
        info_bar.setFixedHeight(30)
        info_bar.setStyleSheet("border-top: 1px solid #111111;")
        info_row = QHBoxLayout(info_bar)
        info_row.setContentsMargins(22, 0, 22, 0)
        info_row.setSpacing(10)

        # Simbol (mono, baby blue)
        self._tb_symbol = QLabel("—")
        self._tb_symbol.setStyleSheet(
            "color: #93C5FD;"
            "font-size: 12px;"
            "font-weight: 600;"
            "font-family: 'SF Mono', 'Menlo', monospace;"
        )
        info_row.addWidget(self._tb_symbol)

        # Separator subtire
        sep = QLabel("/")
        sep.setStyleSheet("color: #1C1C1C; font-size: 12px;")
        info_row.addWidget(sep)

        # Numele comoditatii (ex: "Gold")
        self._tb_name = QLabel("")
        self._tb_name.setStyleSheet(
            "color: #F1F5F9;"
            "font-size: 13px;"
            "font-weight: 600;"
        )
        info_row.addWidget(self._tb_name)

        # Pretul curent (mono)
        self._tb_price = QLabel("")
        self._tb_price.setStyleSheet(
            "color: #F1F5F9;"
            "font-size: 13px;"
            "font-weight: 500;"
            "font-family: 'SF Mono', 'Menlo', monospace;"
        )
        info_row.addWidget(self._tb_price)

        # Indicator dot 6x6
        self._tb_dot = QLabel("")
        self._tb_dot.setFixedSize(6, 6)
        self._tb_dot.setStyleSheet("background: #1C1C1C; border-radius: 3px;")
        info_row.addWidget(self._tb_dot)

        info_row.addStretch()
        vbox.addWidget(info_bar)

        return container

    # ── Public loading API ─────────────────────────────────────────────────────

    def show_loading(self, is_loading: bool, message: str = "Fetching data...") -> None:
        """
        Arata sau ascunde overlay-ul animat (GIF spinner + mesaj).

        Rutare automata dupa tab-ul activ:
            Tab 0 (Macro)   -> _map_overlay
            Tab 1 (Trading) -> _chart_overlay

        Apelat de backend / QThread workers:
            window.show_loading(True,  "Fetching market data...")
            window.show_loading(False)
        """
        overlay = (
            self._map_overlay if self._tabs.currentIndex() == 0
            else self._chart_overlay
        )
        if is_loading:
            overlay.show_loading(message)
        else:
            overlay.hide_loading()

    # ── Injection API (neschimbat) ─────────────────────────────────────────────

    def set_map_widget(self, widget: QWidget) -> None:
        """Injecteaza widget harta in Tab 0. Scoate placeholder-ul la primul apel."""
        if self._map_placeholder is not None:
            self._map_placeholder.setParent(None)
            self._map_placeholder = None
        while self._map_layout.count():
            item = self._map_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._map_layout.addWidget(widget)
        supports_loading_events = (
            hasattr(widget, "load_started") and hasattr(widget, "load_finished")
        )
        if supports_loading_events:
            widget.load_started.connect(
                lambda: self._map_overlay.show_loading("Loading map...")
            )
            widget.load_finished.connect(
                lambda _ok: self._map_overlay.hide_loading()
            )
            self._map_overlay.show_loading("Loading map...")

    def set_chart_widget(self, widget: QWidget) -> None:
        """Injecteaza PanelChart (candlestick + toolbar) in Tab 1."""
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._chart_layout.addWidget(widget)

    # ── Trading Desk update contract (bridge.py — neschimbat) ─────────────────

    def update_news(self, items: list[dict]) -> None:
        self.panel_news.update_news(items)

    def update_insight(self, text: str) -> None:
        self.panel_ai.update_insight(text)

    def set_fetching(self, symbol: str) -> None:
        """Loading ON — apelat imediat dupa commodity_changed."""
        self._current_symbol = symbol
        self._tb_symbol.setText(symbol)
        self._tb_name.setText("")
        self._tb_price.setText("loading...")
        self._tb_price.setStyleSheet(
            "color: #374151; font-size: 13px; font-weight: 400;"
            "font-family: 'SF Mono', 'Menlo', monospace;"
        )
        self._tb_dot.setStyleSheet("background: #93C5FD; border-radius: 3px;")
        self._status_bar.showMessage(f"Fetching data for {symbol}...")
        self.panel_ai.set_loading(True)
        self._chart_overlay.show_loading("Fetching chart data...")

    def set_loading(self, loading: bool) -> None:
        """Apelat de bridge.py cand QThread termina."""
        self.panel_ai.set_loading(loading)
        if not loading:
            self._chart_overlay.hide_loading()

    def update_status(self, symbol: str, price: float | None) -> None:
        """Actualizeaza header-ul Tab 1 cu pretul live."""
        from config import SYMBOLS
        ts = datetime.now().strftime("%H:%M:%S")
        name = SYMBOLS.get(symbol, "")
        self._current_symbol = symbol
        self._tb_symbol.setText(symbol)
        self._tb_name.setText(name)

        if price is not None:
            self._tb_price.setText(f"{price:,.3f}")
            self._tb_price.setStyleSheet(
                "color: #F1F5F9; font-size: 13px; font-weight: 500;"
                "font-family: 'SF Mono', 'Menlo', monospace;"
            )
            self._tb_dot.setStyleSheet("background: #4ADE80; border-radius: 3px;")
            self._status_bar.showMessage(
                f"{symbol}    {name}    {price:,.3f}    {ts}"
            )
        else:
            self._tb_price.setText("—")
            self._tb_price.setStyleSheet(
                "color: #374151; font-size: 13px; font-weight: 500;"
                "font-family: 'SF Mono', 'Menlo', monospace;"
            )
            self._tb_dot.setStyleSheet("background: #1C1C1C; border-radius: 3px;")
            self._status_bar.showMessage(f"{symbol}    {ts}")

    # ── World Macro helpers ────────────────────────────────────────────────────

    def update_macro_news(self, items: list[dict]) -> None:
        self.macro_news.update_news(items)

    def update_macro_insight(self, text: str) -> None:
        self.macro_ai.update_insight(text)

    def switch_to_macro(self) -> None:
        self._tabs.setCurrentIndex(0)

    def switch_to_trading(self) -> None:
        self._tabs.setCurrentIndex(1)
