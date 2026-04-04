"""Pattern matching simulator for backtesting."""

from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from src.data.config import config
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION


class PatternSimulator:
    """Simulates strategy performance on similar historical patterns."""

    def __init__(self) -> None:
        """Initialize the pattern simulator."""
        self.qdrant = QdrantClient(url=config.qdrant_url)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.collection_name = PRICE_PATTERNS_COLLECTION.name

    def find_similar_patterns(
        self,
        commodity: str,
        current_prices: list[float],
        current_volumes: list[int],
        top_k: int = 50,
    ) -> list[dict[str, Any]]:
        """Find similar historical patterns.

        Args:
            commodity: Commodity symbol
            current_prices: Current price series
            current_volumes: Current volume series
            top_k: Number of similar patterns to find

        Returns:
            List of similar patterns with their future returns
        """
        # Create embedding for current pattern
        embedding = self._create_pattern_embedding(current_prices, current_volumes)

        # Search in Qdrant
        results = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=top_k,
            query_filter={
                "must": [
                    {"key": "commodity", "match": {"value": commodity}}
                ]
            },
        ).points

        patterns = []
        for result in results:
            payload = result.payload
            patterns.append({
                "pattern_id": result.id,
                "similarity": result.score,
                "date": payload.get("date"),
                "next_7d_return": payload.get("next_7d_return", 0),
                "next_30d_return": payload.get("next_30d_return", 0),
                "max_drawdown_7d": payload.get("max_drawdown_7d", 0),
                "volatility_regime": payload.get("volatility_regime", "medium"),
                "prices": payload.get("prices", []),
            })

        return patterns

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
        # Normalize prices
        if not prices or prices[0] == 0:
            normalized = [0.0] * len(prices)
        else:
            normalized = [(p / prices[0] - 1) * 100 for p in prices]

        # Normalize volumes
        if volumes and sum(volumes) > 0:
            avg_vol = sum(volumes) / len(volumes)
            normalized_vol = [(v / avg_vol - 1) * 100 for v in volumes]
        else:
            normalized_vol = [0.0] * len(volumes)

        # Create description
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
        """Create text description of pattern."""
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

        if volatility > 3:
            vol_regime = "high volatility"
        elif volatility > 1.5:
            vol_regime = "medium volatility"
        else:
            vol_regime = "low volatility"

        return f"{trend} with {vol_regime}"

    def simulate_strategy(
        self,
        commodity: str,
        current_prices: list[float],
        current_volumes: list[int],
        strategy: dict[str, Any],
        min_sample_size: int = 20,
    ) -> dict[str, Any]:
        """Simulate a strategy on similar historical patterns.

        Args:
            commodity: Commodity symbol
            current_prices: Current price series
            current_volumes: Current volume series
            strategy: Strategy definition with entry/exit rules
            min_sample_size: Minimum number of patterns required

        Returns:
            Simulation results with metrics
        """
        # Find similar patterns
        patterns = self.find_similar_patterns(
            commodity, current_prices, current_volumes, top_k=100
        )

        if len(patterns) < min_sample_size:
            return {
                "valid": False,
                "error": f"Insufficient patterns: {len(patterns)} < {min_sample_size}",
                "sample_size": len(patterns),
            }

        # Simulate trades on each pattern
        trades = []
        for pattern in patterns:
            trade_result = self._simulate_trade(pattern, strategy)
            if trade_result:
                trades.append(trade_result)

        if not trades:
            return {
                "valid": False,
                "error": "No valid trades generated",
                "sample_size": len(patterns),
            }

        # Calculate metrics
        returns = [t["return"] for t in trades]
        equity_curve = self._build_equity_curve(returns)

        from src.backtest.metrics import calculate_all_metrics

        metrics = calculate_all_metrics(returns, equity_curve)
        metrics["sample_size"] = len(patterns)
        metrics["valid"] = True

        # Add pattern analysis
        metrics["avg_pattern_similarity"] = np.mean(
            [p["similarity"] for p in patterns[:len(trades)]]
        )
        metrics["pattern_returns_7d"] = [p["next_7d_return"] for p in patterns[:10]]
        metrics["pattern_returns_30d"] = [p["next_30d_return"] for p in patterns[:10]]

        return metrics

    def _simulate_trade(
        self, pattern: dict[str, Any], strategy: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Simulate a single trade on a historical pattern.

        Args:
            pattern: Historical pattern data
            strategy: Strategy rules

        Returns:
            Trade result or None if invalid
        """
        # Get pattern prices
        prices = pattern.get("prices", [])
        if not prices:
            return None

        entry_price = prices[-1]  # Enter at end of pattern
        recommendation = strategy.get("recommendation", "BUY").upper()

        # Get target and stop from strategy
        target_pct = strategy.get("target_pct", 0.03)  # 3% default
        stop_pct = strategy.get("stop_pct", 0.02)  # 2% default

        if recommendation == "BUY":
            target_price = entry_price * (1 + target_pct)
            stop_price = entry_price * (1 - stop_pct)
        else:  # SELL
            target_price = entry_price * (1 - target_pct)
            stop_price = entry_price * (1 + stop_pct)

        # Simulate using actual future returns from pattern
        return_7d = pattern.get("next_7d_return", 0)

        # Determine outcome
        if recommendation == "BUY":
            price_change = return_7d
            exit_price = entry_price * (1 + price_change / 100)
        else:
            price_change = -return_7d
            exit_price = entry_price * (1 + price_change / 100)

        # Check if target or stop was hit
        hit_target = False
        hit_stop = False

        if recommendation == "BUY":
            if exit_price >= target_price:
                hit_target = True
            elif exit_price <= stop_price:
                hit_stop = True
        else:
            if exit_price <= target_price:
                hit_target = True
            elif exit_price >= stop_price:
                hit_stop = True

        # Calculate actual return
        if hit_target:
            actual_return = target_pct * 100
        elif hit_stop:
            actual_return = -stop_pct * 100
        else:
            actual_return = price_change

        return {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "return": actual_return,
            "hit_target": hit_target,
            "hit_stop": hit_stop,
            "pattern_date": pattern.get("date"),
            "similarity": pattern.get("similarity"),
        }

    def _build_equity_curve(self, returns: list[float]) -> list[float]:
        """Build equity curve from returns.

        Args:
            returns: List of trade returns

        Returns:
            Equity curve values
        """
        equity = [100]  # Start with $100
        for ret in returns:
            equity.append(equity[-1] * (1 + ret / 100))
        return equity

    def get_pattern_distribution(
        self, commodity: str
    ) -> dict[str, Any]:
        """Get distribution of patterns for a commodity.

        Args:
            commodity: Commodity symbol

        Returns:
            Distribution statistics
        """
        try:
            results = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter={
                    "must": [
                        {"key": "commodity", "match": {"value": commodity}}
                    ]
                },
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            patterns = results[0]
            if not patterns:
                return {"count": 0}

            returns_7d = [p.payload.get("next_7d_return", 0) for p in patterns]
            returns_30d = [p.payload.get("next_30d_return", 0) for p in patterns]

            return {
                "count": len(patterns),
                "avg_7d_return": np.mean(returns_7d),
                "avg_30d_return": np.mean(returns_30d),
                "std_7d": np.std(returns_7d),
                "std_30d": np.std(returns_30d),
                "win_rate_7d": sum(1 for r in returns_7d if r > 0) / len(returns_7d),
                "win_rate_30d": sum(1 for r in returns_30d if r > 0) / len(returns_30d),
            }

        except Exception as e:
            return {"count": 0, "error": str(e)}
