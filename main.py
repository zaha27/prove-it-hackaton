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
    from ui.macro_map import MacroMapView
    macro_map = MacroMapView()
    window.set_map_widget(macro_map)

    _MAP_COMMODITIES = ["GOLD", "OIL", "SILVER", "NATURAL_GAS", "WHEAT", "COPPER"]

    # Load live news markers on startup
    macro_map.load_macro_data(_MAP_COMMODITIES)

    # Reload every 10 minutes
    map_timer = QTimer()
    map_timer.timeout.connect(lambda: macro_map.load_macro_data(_MAP_COMMODITIES))
    map_timer.start(MAP_REFRESH_INTERVAL_MS)

    # Wire Trading Desk → data layer (no mock)
    from bridge import AppBridge
    bridge = AppBridge(window, panel_chart)

    window.show()
    # Show investor profile wizard on first launch (no user.json yet)
    window.open_profile_if_new()
    window.sidebar.select_first()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
