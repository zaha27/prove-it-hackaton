"""
charts/panel_chart.py — Chart panel with range/interval toolbar and indicator selector.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QButtonGroup,
)
from PyQt6.QtCore import pyqtSignal

from charts.chart_widget import ChartWidget

logger = logging.getLogger(__name__)

_RANGES = ["6M", "1Y", "5Y", "Max"]
_INTERVALS = ["1D", "1W", "1M"]
_INDICATORS = ["None", "Bollinger Bands", "RSI", "MACD"]


class PanelChart(QWidget):
    """
    Chart panel combining ChartWidget with a range/interval/indicator toolbar.

    Signals:
        timeframe_changed(str, str): emitted when the user selects a range or interval.
    """

    timeframe_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chart_widget = ChartWidget()
        self._active_range = "1Y"
        self._active_interval = "1D"
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._chart_widget, stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(70)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #1C1C1C;")
        vbox = QVBoxLayout(bar)
        vbox.setContentsMargins(18, 6, 18, 6)
        vbox.setSpacing(4)

        _BTN_STYLE = (
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

        range_row = QHBoxLayout()
        range_row.setSpacing(4)
        range_row.addWidget(self._make_toolbar_label("Range"))
        self._range_group = QButtonGroup(self)
        self._range_group.setExclusive(True)
        self._range_buttons: dict[str, QPushButton] = {}
        for value in _RANGES:
            btn = QPushButton(value)
            btn.setCheckable(True)
            btn.setChecked(value == self._active_range)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda checked, v=value: self._on_range(v))
            self._range_group.addButton(btn)
            self._range_buttons[value] = btn
            range_row.addWidget(btn)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(4)
        interval_row.addWidget(self._make_toolbar_label("Interval"))
        self._interval_group = QButtonGroup(self)
        self._interval_group.setExclusive(True)
        self._interval_buttons: dict[str, QPushButton] = {}
        for value in _INTERVALS:
            btn = QPushButton(value)
            btn.setCheckable(True)
            btn.setChecked(value == self._active_interval)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda checked, v=value: self._on_interval(v))
            self._interval_group.addButton(btn)
            self._interval_buttons[value] = btn
            interval_row.addWidget(btn)

        range_row.addSpacing(16)
        lbl2 = QLabel("Indicator")
        lbl2.setStyleSheet(
            "color:#374151; font-size:11px; font-weight:500;"
            "letter-spacing:0.3px; margin-right:4px;"
        )
        range_row.addWidget(lbl2)

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
        range_row.addWidget(self._indicator_combo)
        range_row.addStretch()
        interval_row.addStretch()

        vbox.addLayout(range_row)
        vbox.addLayout(interval_row)
        return bar

    @staticmethod
    def _make_toolbar_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color:#374151; font-size:11px; font-weight:500;"
            "letter-spacing:0.3px; margin-right:4px;"
        )
        return lbl

    def _on_range(self, value: str) -> None:
        self._active_range = value
        self.timeframe_changed.emit(self._active_range, self._active_interval)

    def _on_interval(self, value: str) -> None:
        self._active_interval = value
        self.timeframe_changed.emit(self._active_range, self._active_interval)

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
