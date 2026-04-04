"""Main entry point for the AI Commodity Price Intelligence Platform."""

from src.data.api.data_api import (
    get_ai_insight,
    get_news,
    get_price_data,
    get_supported_commodities,
    init_backend,
)


def main():
    """Run the application."""
    print("=" * 60)
    print("AI Commodity Price Intelligence Platform")
    print("=" * 60)

    # Initialize backend services
    print("\nInitializing backend services...")
    try:
        init_backend()
        print("Backend initialized successfully!")
    except Exception as e:
        print(f"Warning: Backend initialization issue: {e}")
        print("Continuing with limited functionality...")

    # Show supported commodities
    commodities = get_supported_commodities()
    print(f"\nSupported commodities: {', '.join(commodities)}")

    # Example usage
    print("\n" + "=" * 60)
    print("Example: Fetching GOLD data")
    print("=" * 60)

    try:
        # Get price data
        price_data = get_price_data("GOLD", period="5d")
        print(f"\nPrice Data for GOLD:")
        print(f"  Latest price: ${price_data.close[-1]:,.2f}")
        print(f"  Data points: {len(price_data.dates)}")

        # Get news
        news = get_news("GOLD", days=3, limit=3)
        print(f"\nRecent News ({len(news)} articles):")
        for article in news[:3]:
            print(f"  - {article.title} ({article.sentiment})")

        # Get AI insight
        print("\nGenerating AI insight...")
        insight = get_ai_insight("GOLD")
        print(f"\nAI Insight for GOLD:")
        print(f"  Summary: {insight.summary}")
        print(f"  Sentiment: {insight.sentiment}")
        print(f"  Confidence: {insight.confidence:.0%}")

    except Exception as e:
        print(f"\nError fetching data: {e}")
        print("\nNote: Make sure you have:")
        print("  1. Created config/.env with your API keys")
        print("  2. Installed dependencies: uv sync")
        print("  3. Qdrant running (if using vector store)")

    print("\n" + "=" * 60)
    print("Backend is ready for integration with UI!")
    print("=" * 60)
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

    # Tab 1 — Trading Desk: candlestick chart
    from charts.panel_chart import PanelChart
    panel_chart = PanelChart()
    window.set_chart_widget(panel_chart)

    # Tab 0 — World Macro View: geo map (mock events in --mock, empty base otherwise)
    from charts.world_map_widget import WorldMapWidget
    from data.mock_data import get_macro_events
    macro_map = WorldMapWidget()
    window.set_map_widget(macro_map)
    if use_mock:
        macro_map.load_events(get_macro_events())

    # Wire Trading Desk signals → data layer
    from bridge import AppBridge
    bridge = AppBridge(window, panel_chart, use_mock=use_mock)

    window.show()

    # Auto-select the first commodity on startup
    window.sidebar.select_first()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
