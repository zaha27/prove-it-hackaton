"""
charts/world_map_widget.py — QWebEngineView wrapper for the world macro map.

Usage (in main.py, after window is created):
    from charts.world_map_widget import WorldMapWidget
    macro_map = WorldMapWidget()
    window.set_map_widget(macro_map)

    # When macro event data arrives:
    macro_map.load_events(events_list)   # list[dict] — see world_map_engine contract

    # Or just show commodity exposure layer:
    macro_map.load_events([])
"""
import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView

from charts.world_map_engine import build_world_map, PLACEHOLDER_HTML

logger = logging.getLogger(__name__)


class WorldMapWidget(QWidget):
    """
    Self-contained world map widget powered by Plotly + QWebEngineView.

    Data contract (matches world-monitor NewsItem / Hotspot structure):
        {
            "title":    str,
            "lat":      float,
            "lon":      float,
            "severity": "high" | "medium" | "low",
            "category": str,
            "country":  str,
            "summary":  str,
        }
    """

    load_started = pyqtSignal()
    load_finished = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: list[dict] = []
        self._is_loading = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = QWebEngineView()
        self._view.page().setBackgroundColor(QColor("#080808"))
        self._view.setStyleSheet("background: #080808; border: none;")
        self._view.loadStarted.connect(self._on_load_started)
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.setHtml(PLACEHOLDER_HTML)
        layout.addWidget(self._view)

    def load_events(self, events: list[dict]) -> None:
        """
        Render the world map with geo-located events overlaid on the
        commodity exposure choropleth.

        Pass an empty list to show only the base layer.
        """
        self._events = events
        try:
            html = build_world_map(events)
            self._view.setHtml(html)
        except Exception as exc:
            logger.error("WorldMapWidget render failed: %s", exc)

    def refresh(self) -> None:
        """Re-render with the last loaded events."""
        self.load_events(self._events)

    def is_loading(self) -> bool:
        return self._is_loading

    def _on_load_started(self) -> None:
        self._is_loading = True
        self.load_started.emit()

    def _on_load_finished(self, ok: bool) -> None:
        self._is_loading = False
        self.load_finished.emit(ok)
