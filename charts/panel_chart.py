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
        bar.setFixedHeight(38)
        bar.setStyleSheet("background:#161b22;border-bottom:1px solid #30363d;")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(8, 4, 8, 4)

        hbox.addWidget(QLabel("Timeframe:"))
        self._tf_buttons: dict[str, QPushButton] = {}
        for tf in _TIMEFRAMES:
            btn = QPushButton(tf)
            btn.setFixedWidth(40)
            btn.setCheckable(True)
            btn.setChecked(tf == self._active_tf)
            btn.clicked.connect(lambda checked, t=tf: self._on_timeframe(t))
            btn.setStyleSheet(
                "QPushButton{background:#21262d;color:#cdd9e5;border:1px solid #30363d;"
                "border-radius:3px;padding:2px 4px;}"
                "QPushButton:checked{background:#FFD700;color:#000;}"
            )
            hbox.addWidget(btn)
            self._tf_buttons[tf] = btn

        hbox.addSpacing(20)
        hbox.addWidget(QLabel("Indicator:"))
        self._indicator_combo = QComboBox()
        self._indicator_combo.addItems(_INDICATORS)
        self._indicator_combo.currentTextChanged.connect(self._on_indicator_change)
        self._indicator_combo.setFixedWidth(140)
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
