"""
main.py — Entry point for AI Commodity Analyzer (PyQt6 frontend).

Usage:
    uv run main.py

Backend must be running separately:
    uv run server.py
"""
import sys
import logging

# QWebEngineWidgets MUST be imported before QApplication is created
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAP_REFRESH_INTERVAL_MS = 600_000   # 10 minutes


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setApplicationName("AI Commodity Analyzer")
    app.setOrganizationName("HackTeam")

    from ui.styles.theme import apply_theme
    apply_theme(app)

    from ui.main_window import MainWindow
    window = MainWindow()

    # Tab 1 — Trading Desk
    from charts.panel_chart import PanelChart
    panel_chart = PanelChart()
    window.set_chart_widget(panel_chart)

    # Tab 0 — World Macro View
    from charts.world_map_widget import WorldMapWidget
    macro_map = WorldMapWidget()
    window.set_map_widget(macro_map)

    def _load_map_events() -> None:
        from data.backend_client import is_backend_available, get_macro_events
        try:
            if is_backend_available():
                events = get_macro_events()
                macro_map.load_events(events)
                logger.info("World map: loaded %d live events", len(events))
            else:
                logger.warning("World map: backend unavailable, map stays empty")
                macro_map.load_events([])
        except Exception as exc:
            logger.error("World map load failed: %s", exc)
            macro_map.load_events([])

    # Load map on startup
    _load_map_events()

    # Reload every 10 minutes
    map_timer = QTimer()
    map_timer.timeout.connect(_load_map_events)
    map_timer.start(MAP_REFRESH_INTERVAL_MS)

    # Wire Trading Desk → data layer (no mock)
    from bridge import AppBridge
    bridge = AppBridge(window, panel_chart)

    window.show()
    window.sidebar.select_first()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
