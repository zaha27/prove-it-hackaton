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


if __name__ == "__main__":
    main()
