#!/usr/bin/env python3
"""Start the deep research agent for continuous learning."""

import sys
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rl.deep_researcher import DeepResearcher

def main():
    """Main entry point."""
    print("=" * 60)
    print("🧠 Deep Research Agent (Powered by DeepSeek)")
    print("=" * 60)
    print()

    researcher = DeepResearcher()

    # Check health
    print("🔍 Checking component health...")
    health = researcher.check_health()

    print(f"  DeepSeek API: {health['deepseek']['status']} ({health['deepseek']['model']})")
    if health['deepseek']['status'] == "unconfigured":
        print("  ⚠️  DEEPSEEK_API_KEY not set in .env")
        return 1

    print(f"  Qdrant: {health['qdrant']['status']}")
    print(f"  Research dir: {health['research_dir']}")

    print()
    print("🔄 Starting continuous learning loop...")
    print("  Press Ctrl+C to stop")
    print()

    try:
        researcher.continuous_learning_loop(interval_minutes=60)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

    return 0

if __name__ == "__main__":
    sys.exit(main())