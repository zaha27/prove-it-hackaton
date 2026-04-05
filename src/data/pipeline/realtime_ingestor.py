"""Real-time data ingestion to Qdrant for live market data."""

import hashlib
import threading
from collections import deque
from datetime import datetime
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from src.data.config import config
from src.data.ingestion.embedding_utils import (
    create_pattern_embedding,
    describe_pattern,
    qdrant_upsert_with_retry,
)
from src.data.models.price import PriceData
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION


class RealtimeIngestor:
    """Ingests real-time market data into Qdrant for immediate RL context."""

    def __init__(self) -> None:
        """Initialize the realtime ingestor."""
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.collection_name = PRICE_PATTERNS_COLLECTION.name

        self._buffer_size = 20
        # deque with maxlen handles eviction automatically
        self._price_buffer: dict[str, deque[dict[str, Any]]] = {
            commodity: deque(maxlen=self._buffer_size)
            for commodity in ("GOLD", "SILVER", "OIL", "NATURAL_GAS", "WHEAT", "COPPER")
        }
        # Per-commodity locks to avoid contention between different symbols
        self._locks: dict[str, threading.Lock] = {
            commodity: threading.Lock()
            for commodity in self._price_buffer
        }

    def ingest_price_tick(
        self,
        commodity: str,
        price: float,
        volume: int,
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """Ingest a single price tick.

        Args:
            commodity: Commodity symbol
            price: Current price
            volume: Trading volume
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Ingestion result with pattern ID
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Append under lock, then snapshot for pattern creation
        with self._locks[commodity]:
            self._price_buffer[commodity].append({
                "price": price,
                "volume": volume,
                "timestamp": timestamp.isoformat(),
            })
            buffer_snapshot = list(self._price_buffer[commodity])

        if len(buffer_snapshot) < self._buffer_size:
            return {"status": "buffering", "buffer_size": len(buffer_snapshot)}

        # Qdrant write happens outside the lock to avoid blocking other ticks
        pattern_id = self._store_live_pattern(commodity, buffer_snapshot)

        return {
            "status": "ingested",
            "pattern_id": pattern_id,
            "commodity": commodity,
            "timestamp": timestamp.isoformat(),
        }

    def _store_live_pattern(self, commodity: str, buffer: list[dict[str, Any]]) -> int:
        """Store a buffer snapshot as a live pattern in Qdrant.

        Args:
            commodity: Commodity symbol
            buffer: Snapshot of the price buffer (list of tick dicts)

        Returns:
            Pattern ID stored in Qdrant
        """
        from qdrant_client.models import PointStruct

        prices = [p["price"] for p in buffer]
        volumes = [p["volume"] for p in buffer]

        embedding = create_pattern_embedding(prices, volumes, self.embedding_model)

        volatility = (
            float(np.std([(prices[i] / prices[i - 1] - 1) * 100 for i in range(1, len(prices))]))
            if len(prices) > 1
            else 0.0
        )

        timestamp = datetime.utcnow()
        content = f"{commodity}:live:{timestamp.isoformat()}"
        pattern_id = int(hashlib.md5(content.encode()).hexdigest(), 16) & ((1 << 63) - 1)

        if volatility > 2:
            vol_regime = "high"
        elif volatility > 1:
            vol_regime = "medium"
        else:
            vol_regime = "low"

        point = PointStruct(
            id=pattern_id,
            vector=embedding,
            payload={
                "commodity": commodity,
                "date": timestamp.isoformat(),
                "pattern_window": len(prices),
                "prices": prices,
                "volumes": volumes,
                "volatility_regime": vol_regime,
                "is_live": True,
                "next_7d_return": None,
                "next_30d_return": None,
                "max_drawdown_7d": None,
                "ingested_at": timestamp.isoformat(),
            },
        )

        qdrant_upsert_with_retry(self.qdrant, self.collection_name, [point])
        return pattern_id

    def get_buffer_status(self) -> dict[str, Any]:
        """Get status of price buffers.

        Returns:
            Buffer status for each commodity
        """
        result: dict[str, Any] = {}
        for commodity, lock in self._locks.items():
            with lock:
                buf = list(self._price_buffer[commodity])
            result[commodity] = {
                "size": len(buf),
                "full": len(buf) >= self._buffer_size,
                "latest_price": buf[-1]["price"] if buf else None,
                "latest_timestamp": buf[-1]["timestamp"] if buf else None,
            }
        return result

    def clear_buffer(self, commodity: str | None = None) -> None:
        """Clear price buffer(s).

        Args:
            commodity: Specific commodity or None for all
        """
        targets = [commodity] if commodity else list(self._price_buffer.keys())
        for key in targets:
            with self._locks[key]:
                self._price_buffer[key].clear()
