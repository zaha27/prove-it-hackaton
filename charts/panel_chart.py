"""
charts/panel_chart.py — Chart panel with timeframe toolbar and indicator selector.
# TODO: Dev2 — wire timeframe buttons to re-fetch data for the selected period
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel,
)
from PyQt6.QtCore import pyqtSignal

from charts.chart_widget import ChartWidget

logger = logging.getLogger(__name__)

_TIMEFRAMES = ["1W", "1M", "3M", "6M", "1Y"]
_INDICATORS = ["None", "Bollinger Bands", "RSI", "MACD"]


class PanelChart(QWidget):
    """
    Chart panel combining ChartWidget with a timeframe/indicator toolbar.

    Signals:
        timeframe_changed(str): emitted when the user selects a different timeframe.
    """

    timeframe_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart_widget = ChartWidget()
        self._active_tf = "1M"
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._chart_widget, stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(42)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #1C1C1C;")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(18, 0, 18, 0)
        hbox.setSpacing(4)

        lbl = QLabel("Timeframe")
        lbl.setStyleSheet(
            "color:#374151; font-size:11px; font-weight:500;"
            "letter-spacing:0.3px; margin-right:4px;"
        )
        hbox.addWidget(lbl)

        _TF_BTN = (
            "QPushButton {"
            "  background:#111111; color:#6B7280;"
            "  border:1px solid #1C1C1C; border-radius:5px;"
            "  padding:2px 10px; font-size:12px; font-weight:500; min-width:34px;"
            "}"
            "QPushButton:hover { background:#1C1C1C; color:#D1D5DB; border-color:#262626; }"
            "QPushButton:checked {"
            "  background:#1E3A5F; border-color:#93C5FD;"
            "  color:#93C5FD; font-weight:600;"
            "}"
        )
        self._tf_buttons: dict[str, QPushButton] = {}
        for tf in _TIMEFRAMES:
            btn = QPushButton(tf)
            btn.setCheckable(True)
            btn.setChecked(tf == self._active_tf)
            btn.setStyleSheet(_TF_BTN)
            btn.clicked.connect(lambda checked, t=tf: self._on_timeframe(t))
            hbox.addWidget(btn)
            self._tf_buttons[tf] = btn

        hbox.addSpacing(16)

        lbl2 = QLabel("Indicator")
        lbl2.setStyleSheet(
            "color:#374151; font-size:11px; font-weight:500;"
            "letter-spacing:0.3px; margin-right:4px;"
        )
        hbox.addWidget(lbl2)

        self._indicator_combo = QComboBox()
        self._indicator_combo.addItems(_INDICATORS)
        self._indicator_combo.currentTextChanged.connect(self._on_indicator_change)
        self._indicator_combo.setFixedWidth(140)
        self._indicator_combo.setStyleSheet(
            "QComboBox { background:#111111; color:#6B7280;"
            "  border:1px solid #1C1C1C; border-radius:5px;"
            "  padding:3px 10px; font-size:12px; }"
            "QComboBox:hover { border-color:#262626; color:#D1D5DB; }"
            "QComboBox QAbstractItemView {"
            "  background:#111111; color:#D1D5DB;"
            "  border:1px solid #1C1C1C; selection-background-color:#1E3A5F; }"
        )
        hbox.addWidget(self._indicator_combo)
        hbox.addStretch()
        return bar

    def _on_timeframe(self, tf: str) -> None:
        self._active_tf = tf
        for name, btn in self._tf_buttons.items():
            btn.setChecked(name == tf)
        self.timeframe_changed.emit(tf)
        # TODO: Dev2 — trigger re-fetch for the selected timeframe period

    def _on_indicator_change(self, text: str) -> None:
        mapping = {
            "None": "none",
            "Bollinger Bands": "bollinger",
            "RSI": "rsi",
            "MACD": "macd",
        }
        self._chart_widget.set_indicator(mapping.get(text, "none"))

    def load_data(self, ohlcv: dict) -> None:
        """Forward OHLCV data to the inner ChartWidget."""
        self._chart_widget.load_data(ohlcv)

    def show_placeholder(self) -> None:
        self._chart_widget.show_placeholder()

    @property
    def chart_widget(self) -> ChartWidget:
        return self._chart_widget
