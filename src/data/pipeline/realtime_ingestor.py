"""Real-time data ingestion to Qdrant for live market data."""

import hashlib
import uuid
from datetime import datetime
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from src.data.config import config
from src.data.models.price import PriceData
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION


class RealtimeIngestor:
    """Ingests real-time market data into Qdrant for immediate RL context."""

    def __init__(self) -> None:
        """Initialize the realtime ingestor."""
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.collection_name = PRICE_PATTERNS_COLLECTION.name

        # Track recent prices for pattern detection
        self._price_buffer: dict[str, list[dict[str, Any]]] = {
            "GOLD": [],
            "OIL": [],
        }
        self._buffer_size = 20  # Keep last 20 price points

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

        # Add to buffer
        self._price_buffer[commodity].append({
            "price": price,
            "volume": volume,
            "timestamp": timestamp.isoformat(),
        })

        # Maintain buffer size
        if len(self._price_buffer[commodity]) > self._buffer_size:
            self._price_buffer[commodity].pop(0)

        # Only create pattern when buffer is full
        if len(self._price_buffer[commodity]) < self._buffer_size:
            return {"status": "buffering", "buffer_size": len(self._price_buffer[commodity])}

        # Create and store pattern
        pattern_id = self._store_live_pattern(commodity)

        return {
            "status": "ingested",
            "pattern_id": pattern_id,
            "commodity": commodity,
            "timestamp": timestamp.isoformat(),
        }

    def _store_live_pattern(self, commodity: str) -> str:
        """Store current price buffer as a live pattern.

        Args:
            commodity: Commodity symbol

        Returns:
            Pattern ID
        """
        buffer = self._price_buffer[commodity]
        prices = [p["price"] for p in buffer]
        volumes = [p["volume"] for p in buffer]

        # Generate embedding
        embedding = self._create_pattern_embedding(prices, volumes)

        # Create pattern description
        volatility = np.std([(prices[i] / prices[i-1] - 1) * 100 for i in range(1, len(prices))]) if len(prices) > 1 else 0

        pattern_desc = self._describe_pattern(0.0, volatility, prices)

        # Generate unique ID
        timestamp = datetime.utcnow()
        content = f"{commodity}:live:{timestamp.isoformat()}"
        pattern_id = str(uuid.uuid5(uuid.NAMESPACE_OID, content))

        # Determine volatility regime
        if volatility > 2:
            vol_regime = "high"
        elif volatility > 1:
            vol_regime = "medium"
        else:
            vol_regime = "low"

        # Store in Qdrant
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
                "is_live": True,  # Mark as live pattern
                "next_7d_return": None,  # Will be updated later
                "next_30d_return": None,
                "max_drawdown_7d": None,
                "ingested_at": timestamp.isoformat(),
            },
        )

        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return pattern_id

    def _create_pattern_embedding(
        self, prices: list[float], volumes: list[int]
    ) -> list[float]:
        """Create embedding from price pattern.

        Args:
            prices: List of prices
            volumes: List of volumes

        Returns:
            Embedding vector
        """
        # Normalize prices (percentage change from start)
        if not prices or prices[0] == 0:
            normalized = [0.0] * len(prices)
        else:
            normalized = [(p / prices[0] - 1) * 100 for p in prices]

        # Create text description for semantic embedding
        returns = normalized[-1] if normalized else 0
        volatility = np.std(normalized) if len(normalized) > 1 else 0

        pattern_desc = self._describe_pattern(returns, volatility, normalized)

        # Generate embedding
        embedding = self.embedding_model.encode(
            pattern_desc, convert_to_tensor=False
        )
        return embedding.tolist()

    def _describe_pattern(
        self,
        total_return: float,
        volatility: float,
        normalized_prices: list[float],
    ) -> str:
        """Create text description of price pattern.

        Args:
            total_return: Total return percentage
            volatility: Standard deviation
            normalized_prices: Normalized price series

        Returns:
            Text description
        """
        # Determine trend
        if total_return > 5:
            trend = "strong uptrend"
        elif total_return > 2:
            trend = "moderate uptrend"
        elif total_return < -5:
            trend = "strong downtrend"
        elif total_return < -2:
            trend = "moderate downtrend"
        else:
            trend = "sideways consolidation"

        # Determine volatility regime
        if volatility > 3:
            vol_regime = "high volatility"
        elif volatility > 1.5:
            vol_regime = "medium volatility"
        else:
            vol_regime = "low volatility"

        # Check for specific patterns
        patterns = []

        # Breakout detection
        if len(normalized_prices) >= 10:
            first_half = normalized_prices[: len(normalized_prices) // 2]
            second_half = normalized_prices[len(normalized_prices) // 2 :]
            if abs(np.mean(first_half)) < 1 and abs(np.mean(second_half)) > 3:
                patterns.append("breakout pattern")

        # Reversal detection
        if len(normalized_prices) >= 10:
            first_third = normalized_prices[: len(normalized_prices) // 3]
            last_third = normalized_prices[-len(normalized_prices) // 3 :]
            if np.mean(first_third) > 2 and np.mean(last_third) < -1:
                patterns.append("bullish to bearish reversal")
            elif np.mean(first_third) < -2 and np.mean(last_third) > 1:
                patterns.append("bearish to bullish reversal")

        pattern_text = " ".join(patterns) if patterns else "continuation pattern"

        return f"{trend} with {vol_regime} showing {pattern_text}"

    def get_buffer_status(self) -> dict[str, Any]:
        """Get status of price buffers.

        Returns:
            Buffer status for each commodity
        """
        return {
            commodity: {
                "size": len(buffer),
                "full": len(buffer) >= self._buffer_size,
                "latest_price": buffer[-1]["price"] if buffer else None,
                "latest_timestamp": buffer[-1]["timestamp"] if buffer else None,
            }
            for commodity, buffer in self._price_buffer.items()
        }

    def clear_buffer(self, commodity: str | None = None) -> None:
        """Clear price buffer(s).

        Args:
            commodity: Specific commodity or None for all
        """
        if commodity:
            self._price_buffer[commodity] = []
        else:
            for key in self._price_buffer:
                self._price_buffer[key] = []
