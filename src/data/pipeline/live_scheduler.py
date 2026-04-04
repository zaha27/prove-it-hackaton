"""Live data scheduler for periodic market data fetching."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from src.data.services.news_service import NewsService
from src.data.services.price_service import PriceService


@dataclass
class FetchTask:
    """Task configuration for periodic fetching."""

    name: str
    interval_seconds: int
    callback: Callable[[], Any]
    last_run: datetime | None = None
    error_count: int = 0


class LiveScheduler:
    """Async scheduler for live market data fetching."""

    def __init__(
        self,
        price_interval: int = 60,
        news_interval: int = 300,
    ) -> None:
        """Initialize the live scheduler.

        Args:
            price_interval: Seconds between price fetches (default: 60)
            news_interval: Seconds between news fetches (default: 300)
        """
        self.price_service = PriceService()
        self.news_service = NewsService()

        self.price_interval = price_interval
        self.news_interval = news_interval

        self._tasks: list[FetchTask] = []
        self._running = False
        self._commodities = ["GOLD", "OIL"]

        # Statistics
        self.stats = {
            "price_fetches": 0,
            "news_fetches": 0,
            "errors": 0,
            "start_time": None,
        }

    def _create_price_task(self) -> FetchTask:
        """Create price fetching task."""
        async def fetch_prices() -> dict[str, Any]:
            """Fetch latest prices for all commodities."""
            results = {}
            for commodity in self._commodities:
                try:
                    data = self.price_service.get_latest_price(commodity)
                    results[commodity] = data
                    self.stats["price_fetches"] += 1
                except Exception as e:
                    self.stats["errors"] += 1
                    raise ValueError(f"Price fetch failed for {commodity}: {e}") from e
            return results

        return FetchTask(
            name="price_fetch",
            interval_seconds=self.price_interval,
            callback=fetch_prices,
        )

    def _create_news_task(self) -> FetchTask:
        """Create news fetching task."""
        async def fetch_news() -> dict[str, Any]:
            """Fetch latest news for all commodities."""
            results = {}
            for commodity in self._commodities:
                try:
                    articles = self.news_service.fetch_and_embed_news(
                        commodity=commodity,
                        days_back=1,
                        page_size=10,
                    )
                    results[commodity] = len(articles)
                    self.stats["news_fetches"] += 1
                except Exception as e:
                    self.stats["errors"] += 1
                    raise ValueError(f"News fetch failed for {commodity}: {e}") from e
            return results

        return FetchTask(
            name="news_fetch",
            interval_seconds=self.news_interval,
            callback=fetch_news,
        )

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        self.stats["start_time"] = datetime.utcnow()

        # Initialize tasks
        self._tasks = [
            self._create_price_task(),
            self._create_news_task(),
        ]

        # Run initial fetch
        for task in self._tasks:
            await self._execute_task(task)

        # Start periodic execution
        while self._running:
            now = datetime.utcnow()

            for task in self._tasks:
                if task.last_run is None:
                    continue

                elapsed = (now - task.last_run).total_seconds()
                if elapsed >= task.interval_seconds:
                    await self._execute_task(task)

            # Small sleep to prevent CPU spinning
            await asyncio.sleep(1)

    async def _execute_task(self, task: FetchTask) -> None:
        """Execute a fetch task with error handling."""
        try:
            result = await task.callback()
            task.last_run = datetime.utcnow()
            task.error_count = 0
            print(f"[LiveScheduler] {task.name}: Success - {result}")
        except Exception as e:
            task.error_count += 1
            print(f"[LiveScheduler] {task.name}: Error (count={task.error_count}) - {e}")

            # Exponential backoff on repeated errors
            if task.error_count > 3:
                delay = min(2 ** (task.error_count - 3), 60)
                print(f"[LiveScheduler] Backing off {task.name} for {delay}s")
                await asyncio.sleep(delay)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        print("[LiveScheduler] Stopped")

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        uptime = 0.0
        if self.stats["start_time"]:
            uptime = (datetime.utcnow() - self.stats["start_time"]).total_seconds()

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "is_running": self._running,
            "tasks": [
                {
                    "name": t.name,
                    "interval": t.interval_seconds,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "error_count": t.error_count,
                }
                for t in self._tasks
            ],
        }

    async def fetch_once(self) -> dict[str, Any]:
        """Execute one fetch cycle (for testing)."""
        results = {}

        for task in self._tasks:
            try:
                result = await task.callback()
                results[task.name] = result
                task.last_run = datetime.utcnow()
            except Exception as e:
                results[task.name] = f"Error: {e}"

        return results
