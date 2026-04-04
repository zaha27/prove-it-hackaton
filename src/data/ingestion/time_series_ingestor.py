"""Time series data ingestion for historical price patterns."""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from src.data.clients.yfinance_client import YFinanceClient
from src.data.config import config
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION


class TimeSeriesIngestor:
    """Ingests historical price data into vector database for pattern matching."""

    def __init__(self) -> None:
        """Initialize the time series ingestor."""
        self.price_client = YFinanceClient()
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.collection_name = PRICE_PATTERNS_COLLECTION.name

    def _generate_pattern_id(
        self, commodity: str, date: str, window_size: int
    ) -> int:
        """Generate unique numerical ID for a price pattern."""
        content = f"{commodity}:{date}:{window_size}"
        return int(hashlib.md5(content.encode()).hexdigest(), 16) & ((1 << 63) - 1)

    def _create_pattern_embedding(
        self, prices: list[float], volumes: list[int]
    ) -> list[float]:
        """Create embedding from price pattern.

        Args:
            prices: List of closing prices
            volumes: List of volumes

        Returns:
            Embedding vector
        """
        # Normalize prices (percentage change from start)
        if not prices or prices[0] == 0:
            normalized = [0.0] * len(prices)
        else:
            normalized = [(p / prices[0] - 1) * 100 for p in prices]

        # Normalize volumes (relative to average)
        if volumes and sum(volumes) > 0:
            avg_vol = sum(volumes) / len(volumes)
            normalized_vol = [(v / avg_vol - 1) * 100 for v in volumes]
        else:
            normalized_vol = [0.0] * len(volumes)

        # Create text description for semantic embedding
        # This allows pattern matching based on pattern type
        returns = normalized[-1] if normalized else 0
        volatility = np.std(normalized) if len(normalized) > 1 else 0

        pattern_desc = self._describe_pattern(returns, volatility, normalized)

        # Generate embedding from description
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
            volatility: Standard deviation of returns
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

    def _calculate_future_returns(
        self, df: pd.DataFrame, current_idx: int
    ) -> dict[str, float]:
        """Calculate future returns from a given point.

        Args:
            df: DataFrame with price data
            current_idx: Current index

        Returns:
            Dictionary with future returns
        """
        if current_idx >= len(df):
            return {
                "return_7d": 0.0,
                "return_30d": 0.0,
                "max_drawdown_7d": 0.0,
            }

        current_price = df["Close"].iloc[current_idx]

        # 7-day return
        if current_idx + 7 < len(df):
            price_7d = df["Close"].iloc[current_idx + 7]
            return_7d = (price_7d / current_price - 1) * 100

            # Max drawdown in next 7 days
            prices_7d = df["Close"].iloc[current_idx : current_idx + 7]
            peak = prices_7d.expanding().max()
            drawdown = (prices_7d / peak - 1) * 100
            max_dd_7d = drawdown.min()
        else:
            return_7d = 0.0
            max_dd_7d = 0.0

        # 30-day return
        if current_idx + 30 < len(df):
            price_30d = df["Close"].iloc[current_idx + 30]
            return_30d = (price_30d / current_price - 1) * 100
        else:
            return_30d = 0.0

        return {
            "return_7d": return_7d,
            "return_30d": return_30d,
            "max_drawdown_7d": max_dd_7d,
        }

    def ingest_historical_patterns(
        self,
        commodity: str,
        lookback_days: int = 730,
        pattern_window: int = 20,
        step_size: int = 5,
    ) -> int:
        """Ingest historical price patterns into vector DB.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            lookback_days: Days of history to ingest
            pattern_window: Days per pattern window
            step_size: Days between consecutive patterns

        Returns:
            Number of patterns ingested
        """
        print(f"Fetching historical data for {commodity}...")

        # Fetch historical data
        period = f"{lookback_days + pattern_window + 30}d"
        price_data = self.price_client.fetch_ohlcv(commodity, period=period)

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame({
            "Date": price_data.dates,
            "Open": price_data.open,
            "High": price_data.high,
            "Low": price_data.low,
            "Close": price_data.close,
            "Volume": price_data.volume,
        })

        print(f"Processing {len(df)} days of data...")

        points: list[PointStruct] = []

        # Generate patterns with sliding window
        for i in range(0, len(df) - pattern_window - 30, step_size):
            window_df = df.iloc[i : i + pattern_window]

            if len(window_df) < pattern_window:
                continue

            prices = window_df["Close"].tolist()
            volumes = window_df["Volume"].tolist()
            date_str = window_df["Date"].iloc[-1]

            # Generate embedding
            embedding = self._create_pattern_embedding(prices, volumes)

            # Calculate future returns
            future_returns = self._calculate_future_returns(df, i + pattern_window)

            # Determine volatility regime
            returns_series = window_df["Close"].pct_change().dropna()
            volatility = returns_series.std() * 100 if len(returns_series) > 1 else 0

            if volatility > 2:
                vol_regime = "high"
            elif volatility > 1:
                vol_regime = "medium"
            else:
                vol_regime = "low"

            # Create point
            point_id = self._generate_pattern_id(commodity, date_str, pattern_window)

            payload = {
                "commodity": commodity,
                "date": date_str,
                "pattern_window": pattern_window,
                "prices": prices,
                "volumes": volumes,
                "volatility_regime": vol_regime,
                "next_7d_return": future_returns["return_7d"],
                "next_30d_return": future_returns["return_30d"],
                "max_drawdown_7d": future_returns["max_drawdown_7d"],
                "ingested_at": datetime.utcnow().isoformat(),
            }

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Batch upsert to Qdrant
        if points:
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

        print(f"Ingested {len(points)} patterns for {commodity}")
        return len(points)

    def ingest_all_commodities(
        self, lookback_days: int = 730
    ) -> dict[str, int]:
        """Ingest historical patterns for all supported commodities.

        Args:
            lookback_days: Days of history to ingest

        Returns:
            Dictionary mapping commodity to count
        """
        commodities = ["GOLD", "OIL"]
        results = {}

        for commodity in commodities:
            try:
                count = self.ingest_historical_patterns(
                    commodity, lookback_days=lookback_days
                )
                results[commodity] = count
            except Exception as e:
                print(f"Error ingesting {commodity}: {e}")
                results[commodity] = 0

        return results

    def get_pattern_count(self, commodity: str | None = None) -> int:
        """Get total number of patterns in the collection.

        Args:
            commodity: Optional filter by commodity

        Returns:
            Pattern count
        """
        try:
            if commodity:
                # Count with filter
                result = self.qdrant.count(
                    collection_name=self.collection_name,
                    count_filter={
                        "must": [{"key": "commodity", "match": {"value": commodity}}]
                    },
                )
            else:
                result = self.qdrant.count(collection_name=self.collection_name)

            return result.count
        except Exception as e:
            print(f"Error counting patterns: {e}")
            return 0
