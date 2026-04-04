"""Pipeline orchestrator for coordinating live data ingestion."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Any

from src.data.config import config
from src.data.ingestion.time_series_ingestor import TimeSeriesIngestor
from src.data.pipeline.live_scheduler import LiveScheduler
from src.data.pipeline.realtime_ingestor import RealtimeIngestor


class PipelineOrchestrator:
    """Orchestrates the live data pipeline for continuous market data ingestion."""

    def __init__(
        self,
        price_interval: int = 60,
        news_interval: int = 300,
    ) -> None:
        """Initialize the pipeline orchestrator.

        Args:
            price_interval: Seconds between price fetches
            news_interval: Seconds between news fetches
        """
        self.scheduler = LiveScheduler(price_interval, news_interval)
        self.ingestor = RealtimeIngestor()
        self.historical_ingestor = TimeSeriesIngestor()

        self._running = False
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.stats = {
            "start_time": None,
            "total_price_ticks": 0,
            "total_patterns_stored": 0,
            "errors": [],
        }

    async def initialize(self) -> dict[str, Any]:
        """Initialize the pipeline with historical data backfill.

        Returns:
            Initialization results
        """
        print("[Orchestrator] Initializing pipeline...")

        # Check Qdrant connection
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=config.qdrant_url)
            client.get_collections()
            print("[Orchestrator] Qdrant connection: OK")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Qdrant: {e}") from e

        # Check if historical data exists
        pattern_count = self.historical_ingestor.get_pattern_count()
        print(f"[Orchestrator] Existing patterns in Qdrant: {pattern_count}")

        if pattern_count == 0:
            print("[Orchestrator] No historical data found. Running initial backfill...")
            results = self.historical_ingestor.ingest_all_commodities(
                lookback_days=config.backtest_lookback_days
            )
            print(f"[Orchestrator] Historical backfill complete: {results}")
        else:
            results = {"existing_patterns": pattern_count}

        return {
            "status": "initialized",
            "historical_patterns": results,
            "qdrant_url": config.qdrant_url,
        }

    async def run(self) -> None:
        """Run the live data pipeline."""
        print("[Orchestrator] Starting live data pipeline...")

        # Initialize
        await self.initialize()

        self._running = True
        self.stats["start_time"] = datetime.utcnow()

        # Set up signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )

        # Start the scheduler in background
        scheduler_task = asyncio.create_task(self._run_scheduler())

        # Start price tick ingestion
        ingestion_task = asyncio.create_task(self._run_ingestion_loop())

        print("[Orchestrator] Pipeline running. Press Ctrl+C to stop.")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cancel background tasks
        scheduler_task.cancel()
        ingestion_task.cancel()

        try:
            await scheduler_task
            await ingestion_task
        except asyncio.CancelledError:
            pass

        print("[Orchestrator] Pipeline stopped.")

    async def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        try:
            await self.scheduler.start()
        except Exception as e:
            print(f"[Orchestrator] Scheduler error: {e}")
            self.stats["errors"].append({"source": "scheduler", "error": str(e)})
            await self.shutdown()

    async def _run_ingestion_loop(self) -> None:
        """Run the price tick ingestion loop."""
        while self._running:
            try:
                # Fetch latest prices and ingest as ticks
                for commodity in ["GOLD", "OIL"]:
                    try:
                        from src.data.clients.yfinance_client import YFinanceClient
                        client = YFinanceClient()
                        price, _ = client.fetch_latest_price(commodity)

                        # Get volume from latest data
                        price_data = client.fetch_ohlcv(commodity, period="1d")
                        volume = price_data.volume[-1] if price_data.volume else 0

                        # Ingest tick
                        result = self.ingestor.ingest_price_tick(
                            commodity=commodity,
                            price=price,
                            volume=volume,
                        )

                        if result["status"] == "ingested":
                            self.stats["total_patterns_stored"] += 1

                        self.stats["total_price_ticks"] += 1

                    except Exception as e:
                        print(f"[Orchestrator] Ingestion error for {commodity}: {e}")

                # Wait before next tick
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=60,  # Check every minute
                )

            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                print(f"[Orchestrator] Ingestion loop error: {e}")
                self.stats["errors"].append({"source": "ingestion", "error": str(e)})
                await asyncio.sleep(5)

    async def shutdown(self) -> None:
        """Gracefully shutdown the pipeline."""
        print("\n[Orchestrator] Shutdown signal received...")
        self._running = False
        self.scheduler.stop()
        self._shutdown_event.set()

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status.

        Returns:
            Status dictionary
        """
        uptime = 0.0
        if self.stats["start_time"]:
            uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()

        return {
            "is_running": self._running,
            "uptime_seconds": uptime,
            "scheduler_stats": self.scheduler.get_stats(),
            "ingestor_status": self.ingestor.get_buffer_status(),
            "total_price_ticks": self.stats["total_price_ticks"],
            "total_patterns_stored": self.stats["total_patterns_stored"],
            "error_count": len(self.stats["errors"]),
            "recent_errors": self.stats["errors"][-5:] if self.stats["errors"] else [],
        }

    async def run_once(self) -> dict[str, Any]:
        """Run one complete cycle (for testing).

        Returns:
            Cycle results
        """
        print("[Orchestrator] Running single cycle...")

        # Fetch prices
        scheduler_results = await self.scheduler.fetch_once()

        # Ingest ticks
        ingestion_results = {}
        for commodity in ["GOLD", "OIL"]:
            try:
                from src.data.clients.yfinance_client import YFinanceClient
                client = YFinanceClient()
                price, _ = client.fetch_latest_price(commodity)
                price_data = client.fetch_ohlcv(commodity, period="1d")
                volume = price_data.volume[-1] if price_data.volume else 0

                result = self.ingestor.ingest_price_tick(
                    commodity=commodity,
                    price=price,
                    volume=volume,
                )
                ingestion_results[commodity] = result

            except Exception as e:
                ingestion_results[commodity] = f"Error: {e}"

        return {
            "scheduler": scheduler_results,
            "ingestion": ingestion_results,
            "status": "complete",
        }


def main() -> None:
    """Main entry point for the pipeline."""
    orchestrator = PipelineOrchestrator()

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")
    finally:
        status = orchestrator.get_status()
        print(f"\n[Main] Final status: {status}")


if __name__ == "__main__":
    main()
