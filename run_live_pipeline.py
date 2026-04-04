#!/usr/bin/env python3
"""Main entry point for the live trading intelligence pipeline.

This script runs the complete live data pipeline with:
- Yahoo Finance data ingestion (prices every 60s)
- Real-time pattern storage in Qdrant
- RL-ready prediction tracking
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data.pipeline import PipelineOrchestrator


async def main() -> None:
    """Run the live pipeline."""
    print("=" * 60)
    print("AI Commodity Trading Intelligence - Live Pipeline")
    print("=" * 60)
    print()
    print("Data Source: Yahoo Finance (ONLY)")
    print("Commodities: GOLD, OIL")
    print("Price Updates: Every 60 seconds")
    print("Vector DB: Qdrant (localhost:6333)")
    print("RL Tracking: ENABLED")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    orchestrator = PipelineOrchestrator(
        price_interval=60,  # Fetch prices every 60 seconds
        news_interval=300,  # News disabled - Yahoo Finance only
    )

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        print("\n\nShutdown requested by user...")
    finally:
        status = orchestrator.get_status()
        print("\n" + "=" * 60)
        print("Final Status:")
        print(f"  Uptime: {status['uptime_seconds']:.1f} seconds")
        print(f"  Price Ticks: {status['total_price_ticks']}")
        print(f"  Patterns Stored: {status['total_patterns_stored']}")
        print(f"  Errors: {status['error_count']}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
