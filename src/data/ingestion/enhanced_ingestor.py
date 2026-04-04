"""Enhanced time series ingestion with XGBoost features and 10-year support."""

import hashlib
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.data.clients.yfinance_client import YFinanceClient
from src.data.config import config
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION
from src.features.xgboost_features import XGBoostFeatureEngineer


class EnhancedTimeSeriesIngestor:
    """Enhanced ingestor with XGBoost features and 10-year historical data."""

    def __init__(self) -> None:
        """Initialize the enhanced ingestor."""
        self.price_client = YFinanceClient()
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = None  # Lazy load
        self.collection_name = PRICE_PATTERNS_COLLECTION.name
        self.feature_engineer = XGBoostFeatureEngineer()

    def _get_embedding_model(self):
        """Lazy load embedding model."""
        if self.embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(config.embedding_model)
        return self.embedding_model

    def _generate_pattern_id(
        self, commodity: str, date: str, window_size: int
    ) -> int:
        """Generate unique ID for a price pattern."""
        content = f"{commodity}:{date}:{window_size}"
        # Convert to integer for Qdrant
        return int(hashlib.md5(content.encode()).hexdigest(), 16) % (2**63)

    def _create_enhanced_embedding(
        self, features: pd.Series, pattern_desc: str
    ) -> list[float]:
        """Create embedding from features and description.

        Args:
            features: Feature Series
            pattern_desc: Text description of pattern

        Returns:
            Combined embedding vector
        """
        # Get semantic embedding from description
        model = self._get_embedding_model()
        text_embedding = model.encode(pattern_desc, convert_to_tensor=False)

        # Get only numeric feature values
        # Filter to numeric types only (int, float)
        numeric_values = [
            v for v in features.values
            if isinstance(v, (int, float, np.integer, np.floating))
            and not isinstance(v, bool)
        ]
        feature_values = np.array(numeric_values[:50])  # Take first 50 numeric features
        feature_values = np.nan_to_num(feature_values, nan=0.0, posinf=0.0, neginf=0.0)

        # Normalize features
        if len(feature_values) > 0 and np.std(feature_values) > 0:
            feature_values = (feature_values - np.mean(feature_values)) / np.std(feature_values)

        # Pad or truncate to match text embedding size
        target_size = len(text_embedding)
        if len(feature_values) < target_size:
            feature_values = np.pad(
                feature_values, (0, target_size - len(feature_values)), mode='constant'
            )
        else:
            feature_values = feature_values[:target_size]

        # Combine embeddings (weighted average)
        combined = 0.7 * text_embedding + 0.3 * feature_values

        return combined.tolist()

    def _describe_enhanced_pattern(self, features: pd.Series) -> str:
        """Create enhanced text description of pattern.

        Args:
            features: Feature Series

        Returns:
            Rich text description
        """
        parts = []

        # Trend description
        if "return_5d" in features and "return_20d" in features:
            r5 = features["return_5d"]
            r20 = features["return_20d"]

            if r5 > 5 and r20 > 10:
                parts.append("strong bullish trend")
            elif r5 < -5 and r20 < -10:
                parts.append("strong bearish trend")
            elif abs(r5) < 2 and abs(r20) < 5:
                parts.append("consolidation phase")
            elif r5 > 0 and r20 < 0:
                parts.append("short term bounce in downtrend")
            elif r5 < 0 and r20 > 0:
                parts.append("short term pullback in uptrend")
            else:
                parts.append("mixed trend signals")

        # Volatility regime
        if "volatility_20d" in features:
            vol = features["volatility_20d"]
            if vol > 3:
                parts.append("high volatility")
            elif vol > 1.5:
                parts.append("medium volatility")
            else:
                parts.append("low volatility")

        # RSI condition
        if "rsi_14" in features:
            rsi = features["rsi_14"]
            if rsi > 70:
                parts.append("overbought RSI")
            elif rsi < 30:
                parts.append("oversold RSI")
            else:
                parts.append("neutral RSI")

        # Volume condition
        if "volume_ratio_20" in features:
            vr = features["volume_ratio_20"]
            if vr > 2:
                parts.append("extremely high volume")
            elif vr > 1.5:
                parts.append("above average volume")
            elif vr < 0.5:
                parts.append("low volume")

        # MACD condition
        if "macd_diff" in features:
            macd = features["macd_diff"]
            if macd > 0:
                parts.append("bullish MACD")
            else:
                parts.append("bearish MACD")

        # Bollinger Bands
        if "bb_pct" in features:
            bb = features["bb_pct"]
            if bb > 0.8:
                parts.append("near upper Bollinger Band")
            elif bb < 0.2:
                parts.append("near lower Bollinger Band")

        # Pattern detection
        if "is_doji" in features and features["is_doji"]:
            parts.append("doji candlestick")
        if "is_hammer" in features and features["is_hammer"]:
            parts.append("hammer pattern")
        if "breakout_up_20" in features and features["breakout_up_20"]:
            parts.append("20-day breakout")
        if "breakout_down_20" in features and features["breakout_down_20"]:
            parts.append("20-day breakdown")

        return " | ".join(parts) if parts else "neutral pattern"

    def _calculate_future_returns(
        self, df: pd.DataFrame, current_idx: int
    ) -> dict[str, float]:
        """Calculate future returns from a given point."""
        if current_idx >= len(df):
            return {
                "return_1d": 0.0,
                "return_3d": 0.0,
                "return_7d": 0.0,
                "return_14d": 0.0,
                "return_30d": 0.0,
                "max_drawdown_7d": 0.0,
                "max_drawdown_30d": 0.0,
                "volatility_7d": 0.0,
            }

        current_price = df["Close"].iloc[current_idx]

        returns = {}
        for days in [1, 3, 7, 14, 30]:
            if current_idx + days < len(df):
                future_price = df["Close"].iloc[current_idx + days]
                returns[f"return_{days}d"] = (future_price / current_price - 1) * 100

                # Max drawdown
                prices = df["Close"].iloc[current_idx:current_idx + days]
                peak = prices.expanding().max()
                drawdown = (prices / peak - 1) * 100
                returns[f"max_drawdown_{days}d"] = drawdown.min()

                # Volatility
                returns[f"volatility_{days}d"] = prices.pct_change().std() * 100
            else:
                returns[f"return_{days}d"] = 0.0
                returns[f"max_drawdown_{days}d"] = 0.0
                returns[f"volatility_{days}d"] = 0.0

        return returns

    def ingest_historical_patterns(
        self,
        commodity: str,
        lookback_days: int = 3650,  # ~10 years
        pattern_window: int = 20,
        step_size: int = 1,  # Daily patterns for maximum coverage
    ) -> int:
        """Ingest historical price patterns with XGBoost features.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            lookback_days: Days of history to ingest (default 10 years)
            pattern_window: Days per pattern window
            step_size: Days between consecutive patterns

        Returns:
            Number of patterns ingested
        """
        print(f"📊 Fetching {lookback_days} days of historical data for {commodity}...")

        # Fetch historical data - use max period for 10 years
        price_data = self.price_client.fetch_ohlcv(
            commodity, period="max", interval="1d"
        )

        # Convert to DataFrame
        df = pd.DataFrame({
            "Date": price_data.dates,
            "Open": price_data.open,
            "High": price_data.high,
            "Low": price_data.low,
            "Close": price_data.close,
            "Volume": price_data.volume,
        })

        # Limit to lookback_days
        if len(df) > lookback_days:
            df = df.iloc[-lookback_days:].reset_index(drop=True)

        print(f"  Processing {len(df)} days of data...")

        # Engineer features
        print("  🔧 Engineering XGBoost features...")
        df = self.feature_engineer.engineer_features(df)

        print(f"  Generated {len(self.feature_engineer.feature_names)} features")

        points: list[PointStruct] = []

        # Generate patterns with sliding window
        for i in range(0, len(df) - pattern_window - 30, step_size):
            window_df = df.iloc[i:i + pattern_window]
            current_idx = i + pattern_window - 1

            if len(window_df) < pattern_window:
                continue

            # Get current features
            features = df.iloc[current_idx]
            date_val = features["Date"]
            # Handle both string and Timestamp types
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val)

            # Create pattern description
            pattern_desc = self._describe_enhanced_pattern(features)

            # Generate embedding
            embedding = self._create_enhanced_embedding(features, pattern_desc)

            # Calculate future returns
            future_returns = self._calculate_future_returns(df, current_idx + 1)

            # Extract key features for payload (only numeric)
            feature_payload = {}
            for k, v in features.items():
                if k in self.feature_engineer.feature_names:
                    if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                        feature_payload[k] = float(v) if pd.notna(v) else 0.0
                    else:
                        feature_payload[k] = 0.0  # Default for non-numeric

            # Create point
            point_id = self._generate_pattern_id(commodity, date_str, pattern_window)

            payload = {
                "commodity": commodity,
                "date": date_str,
                "pattern_window": pattern_window,
                "pattern_description": pattern_desc,
                "features": feature_payload,
                **future_returns,
                "ingested_at": datetime.utcnow().isoformat(),
            }

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            points.append(point)

            # Progress indicator
            if len(points) % 500 == 0:
                print(f"    Processed {len(points)} patterns...")

        # Batch upsert to Qdrant
        if points:
            print(f"  💾 Storing {len(points)} patterns in Qdrant...")
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

        print(f"✅ Ingested {len(points)} patterns for {commodity}")
        return len(points)

    def ingest_all_commodities(
        self, lookback_days: int = 3650
    ) -> dict[str, int]:
        """Ingest historical patterns for all supported commodities.

        Args:
            lookback_days: Days of history to ingest

        Returns:
            Dictionary mapping commodity to count
        """
        # --- AICI SE ADAUGĂ LISTA COMPLETĂ ---
        commodities = ["GOLD", "SILVER", "OIL", "NATURAL_GAS", "WHEAT", "COPPER"]
        results = {}

        for commodity in commodities:
            try:
                count = self.ingest_historical_patterns(
                    commodity, lookback_days=lookback_days
                )
                results[commodity] = count
            except Exception as e:
                print(f"❌ Error ingesting {commodity}: {e}")
                results[commodity] = 0

        return results

    def calculate_feature_importance(
        self, commodity: str, target_horizon: int = 7
    ) -> dict[str, float]:
        """Calculate feature importance for a commodity.

        Args:
            commodity: Commodity symbol
            target_horizon: Days ahead for target

        Returns:
            Feature importance dictionary
        """
        print(f"🔍 Calculating feature importance for {commodity}...")

        # Fetch data
        price_data = self.price_client.fetch_ohlcv(commodity, period="5y")
        df = pd.DataFrame({
            "Date": price_data.dates,
            "Open": price_data.open,
            "High": price_data.high,
            "Low": price_data.low,
            "Close": price_data.close,
            "Volume": price_data.volume,
        })

        # Engineer features
        df = self.feature_engineer.engineer_features(df)

        # Calculate importance
        importance = self.feature_engineer.get_feature_importance(
            df, target_col=f"return_{target_horizon}d"
        )

        print(f"  Top 10 features for {target_horizon}d prediction:")
        for feat, imp in list(importance.items())[:10]:
            print(f"    {feat}: {imp:.4f}")

        return importance

    def get_pattern_count(self, commodity: str | None = None) -> int:
        """Get total number of patterns in the collection.

        Args:
            commodity: Optional filter by commodity

        Returns:
            Pattern count
        """
        try:
            if commodity:
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
