"""
main.py — Entry point for AI Commodity Analyzer.

Usage:
    uv run main.py           # production mode (requires .env with API keys)
    uv run main.py --mock    # demo mode with hardcoded data (no API keys needed)
"""
import sys
import logging

# QWebEngineWidgets MUST be imported before QApplication is created
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

logger = logging.getLogger(__name__)


def main() -> int:
    use_mock = "--mock" in sys.argv

    if use_mock:
        print("▶ Running in MOCK mode — no API keys required")
    else:
        print("▶ Running in LIVE mode — requires .env with API keys")

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("AI Commodity Analyzer")
    app.setOrganizationName("HackTeam")

    # Apply dark theme
    from ui.styles.theme import apply_theme
    apply_theme(app)

    # Build main window
    from ui.main_window import MainWindow
    window = MainWindow()

    # Build chart panel
    from charts.panel_chart import PanelChart
    panel_chart = PanelChart()
    window.set_chart_widget(panel_chart)

    # Wire everything together
    from bridge import AppBridge
    bridge = AppBridge(window, panel_chart, use_mock=use_mock)

    window.show()

    # Auto-select the first commodity on startup
    window.sidebar.select_first()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
