#!/usr/bin/env python3
"""Start the deep research agent for continuous learning."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.rl.deep_researcher import DeepResearcher


def main():
    """Main entry point."""
    print("=" * 60)
    print("🧠 Deep Research Agent")
    print("=" * 60)
    print()

    researcher = DeepResearcher()

    # Check health
    print("🔍 Checking component health...")
    health = researcher.check_health()

    print(f"  Ollama: {health['ollama']['status']}")
    if not health['ollama'].get('model_available'):
        print(f"  ⚠️  Model {health['ollama'].get('required_model')} not found")
        print("  Run: ollama pull gemma4:2b")
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
