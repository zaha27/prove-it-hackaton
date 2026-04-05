"""Shared embedding, pattern description, and Qdrant retry utilities for ingestors."""

import time
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct


def describe_pattern(
    total_return: float,
    volatility: float,
    normalized_prices: list[float],
) -> str:
    """Create text description of a price pattern.

    Args:
        total_return: Total return percentage over the window
        volatility: Standard deviation of normalized returns
        normalized_prices: Normalized price series (% change from start)

    Returns:
        Human-readable pattern description for embedding
    """
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

    patterns = []

    if len(normalized_prices) >= 10:
        first_half = normalized_prices[: len(normalized_prices) // 2]
        second_half = normalized_prices[len(normalized_prices) // 2 :]
        if abs(np.mean(first_half)) < 1 and abs(np.mean(second_half)) > 3:
            patterns.append("breakout pattern")

    if len(normalized_prices) >= 10:
        first_third = normalized_prices[: len(normalized_prices) // 3]
        last_third = normalized_prices[-len(normalized_prices) // 3 :]
        if np.mean(first_third) > 2 and np.mean(last_third) < -1:
            patterns.append("bullish to bearish reversal")
        elif np.mean(first_third) < -2 and np.mean(last_third) > 1:
            patterns.append("bearish to bullish reversal")

    pattern_text = " ".join(patterns) if patterns else "continuation pattern"
    return f"{trend} with {vol_regime} showing {pattern_text}"


def create_pattern_embedding(
    prices: list[float],
    volumes: list[int],
    embedding_model: Any,
) -> list[float]:
    """Create a semantic embedding from a price/volume pattern.

    Args:
        prices: List of closing prices
        volumes: List of trading volumes (used for future extension)
        embedding_model: SentenceTransformer instance

    Returns:
        Embedding vector as a list of floats
    """
    if not prices or prices[0] == 0:
        normalized = [0.0] * len(prices)
    else:
        normalized = [(p / prices[0] - 1) * 100 for p in prices]

    returns = normalized[-1] if normalized else 0.0
    volatility = float(np.std(normalized)) if len(normalized) > 1 else 0.0

    pattern_desc = describe_pattern(returns, volatility, normalized)
    embedding = embedding_model.encode(pattern_desc, convert_to_tensor=False)
    return embedding.tolist()


def qdrant_upsert_with_retry(
    client: QdrantClient,
    collection_name: str,
    points: list[PointStruct],
    max_retries: int = 3,
) -> None:
    """Upsert points to Qdrant with exponential backoff retry.

    Args:
        client: Qdrant client instance
        collection_name: Target collection name
        points: Points to upsert
        max_retries: Maximum number of attempts before raising

    Raises:
        Exception: Re-raises the last exception if all retries are exhausted
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            client.upsert(collection_name=collection_name, points=points)
            return
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise last_exc  # type: ignore[misc]
