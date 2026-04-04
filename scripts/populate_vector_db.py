#!/usr/bin/env python3
""" vector DB with 10 years of historical data and XGBoost features."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.vector_schema import init_vector_schema
from src.data.ingestion.enhanced_ingestor import EnhancedTimeSeriesIngestor


def main():
    """Main entry point."""
    print("=" * 60)
    print("🚀 Vector DB Population Script")
    print("=" * 60)
    print()

    # Step 1: Initialize collections
    print("📦 Step 1: Initializing vector collections...")
    try:
        init_vector_schema()
        print("  ✓ Collections initialized")
    except Exception as e:
        print(f"  ✗ Error initializing collections: {e}")
        return 1

    print()

    # Step 2: Ingest historical patterns
    print("📊 Step 2: Ingesting historical patterns (10 years)...")
    ingestor = EnhancedTimeSeriesIngestor()

    results = ingestor.ingest_all_commodities(lookback_days=3650)

    print()
    print("📈 Ingestion Results:")
    print("-" * 40)
    total = 0
    for commodity, count in results.items():
        print(f"  {commodity}: {count:,} patterns")
        total += count
    print("-" * 40)
    print(f"  Total: {total:,} patterns")

    print()

    # Step 3: Calculate feature importance
    print("🔍 Step 3: Calculating feature importance...")
    for commodity in ["GOLD", "OIL"]:
        if results.get(commodity, 0) > 0:
            try:
                importance = ingestor.calculate_feature_importance(commodity)
                print(f"  ✓ {commodity} feature importance calculated")
            except Exception as e:
                print(f"  ✗ Error calculating importance for {commodity}: {e}")

    print()
    print("=" * 60)
    print("✅ Population complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
