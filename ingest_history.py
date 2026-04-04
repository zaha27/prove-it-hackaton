#!/usr/bin/env python3
"""Ingest 5-year historical market data into Qdrant for ML training."""

from __future__ import annotations

import argparse
import hashlib
import math
from dataclasses import dataclass
from typing import Any
import logging
from requests.exceptions import RequestException

import numpy as np
import pandas as pd
import yfinance as yf
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config import SYMBOLS
from src.data.config import config as data_config
from src.features.xgboost_features import XGBoostFeatureEngineer

TRAINING_COLLECTION = "historical_training_data"
VECTOR_SIZE = 384
TARGET_HORIZONS = (1, 3, 7, 14, 30)
UPSERT_BATCH_SIZE = 256
SCROLL_BATCH_SIZE = 1000
TRAIN_TEST_SPLIT_RATIO = 0.8

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    symbol: str
    rows_ingested: int


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        return 0.0
    return float(value)


def _feature_vector(feature_values: list[float], size: int = VECTOR_SIZE) -> list[float]:
    """Build a stable numeric embedding vector from engineered features."""
    vec = np.array([_safe_float(v) for v in feature_values], dtype=np.float32)
    vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)
    if vec.size == 0:
        vec = np.zeros(size, dtype=np.float32)
    else:
        if vec.size < size:
            vec = np.pad(vec, (0, size - vec.size), mode="constant")
        else:
            vec = vec[:size]
    return vec.tolist()


def _row_id(symbol: str, date: str) -> int:
    digest = hashlib.sha256(f"{symbol}:{date}".encode("utf-8")).hexdigest()[:16]
    # Qdrant integer IDs must fit signed int64.
    return int(digest, 16) % (2**63)


def _prepare_symbol_dataframe(symbol: str, years: int) -> pd.DataFrame:
    try:
        hist = yf.Ticker(symbol).history(period=f"{years}y", interval="1d", auto_adjust=False)
    except RequestException as exc:
        logger.warning("Network/API error while downloading %s history: %s", symbol, exc)
        return pd.DataFrame()
    except ValueError as exc:
        logger.warning("Invalid symbol or malformed request for %s: %s", symbol, exc)
        return pd.DataFrame()
    except Exception as exc:
        logger.warning("Unexpected failure while downloading %s history: %s", symbol, exc)
        return pd.DataFrame()

    if hist.empty:
        logger.warning("No historical rows returned for %s", symbol)
        return pd.DataFrame()

    hist = hist.reset_index()
    hist["Date"] = pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")
    df = hist[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    return df.reset_index(drop=True)


def _engineer_training_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    fe = XGBoostFeatureEngineer()
    feat_df = fe.engineer_features(df)
    close = feat_df["Close"].replace(0, np.nan)

    for horizon in TARGET_HORIZONS:
        feat_df[f"target_return_{horizon}d"] = feat_df["Close"].shift(-horizon) / close - 1.0

    feature_cols = [c for c in fe.feature_names if c in feat_df.columns]
    required_cols = feature_cols + [f"target_return_{h}d" for h in TARGET_HORIZONS]
    feat_df = feat_df.dropna(subset=required_cols).reset_index(drop=True)
    return feat_df, feature_cols


def _ensure_collection(client: QdrantClient, collection_name: str) -> None:
    collections = client.get_collections().collections
    if collection_name in {c.name for c in collections}:
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def ingest_history(
    years: int = 5,
    collection_name: str = TRAINING_COLLECTION,
) -> list[IngestResult]:
    """Download, engineer, and upsert historical training rows to Qdrant."""
    qdrant = QdrantClient(url=data_config.qdrant_url)
    _ensure_collection(qdrant, collection_name)

    results: list[IngestResult] = []
    for symbol in SYMBOLS:
        raw_df = _prepare_symbol_dataframe(symbol, years=years)
        if raw_df.empty:
            results.append(IngestResult(symbol=symbol, rows_ingested=0))
            continue

        feat_df, feature_cols = _engineer_training_rows(raw_df)
        if feat_df.empty:
            results.append(IngestResult(symbol=symbol, rows_ingested=0))
            continue

        points: list[PointStruct] = []
        for _, row in feat_df.iterrows():
            date_str = str(row["Date"])
            features = {col: _safe_float(row[col]) for col in feature_cols}
            vector = _feature_vector([features[col] for col in feature_cols])
            payload = {
                "symbol": symbol,
                "date": date_str,
                "features": features,
                "target_return_1d": _safe_float(row["target_return_1d"]),
                "target_return_3d": _safe_float(row["target_return_3d"]),
                "target_return_7d": _safe_float(row["target_return_7d"]),
                "target_return_14d": _safe_float(row["target_return_14d"]),
                "target_return_30d": _safe_float(row["target_return_30d"]),
                "source": "historical_training",
            }
            points.append(
                PointStruct(
                    id=_row_id(symbol, date_str),
                    vector=vector,
                    payload=payload,
                )
            )

        for i in range(0, len(points), UPSERT_BATCH_SIZE):
            qdrant.upsert(
                collection_name=collection_name,
                points=points[i : i + UPSERT_BATCH_SIZE],
            )

        results.append(IngestResult(symbol=symbol, rows_ingested=len(points)))

    return results


def get_training_data(
    symbol: str,
    target_horizon: int = 7,
    collection_name: str = TRAINING_COLLECTION,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Load symbol data from Qdrant and return chronological 80/20 split."""
    if target_horizon not in TARGET_HORIZONS:
        raise ValueError(f"Unsupported target horizon: {target_horizon}. Supported: {TARGET_HORIZONS}")

    qdrant = QdrantClient(url=data_config.qdrant_url)
    target_col = f"target_return_{target_horizon}d"

    records: list[dict[str, Any]] = []
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="symbol", match=MatchValue(value=symbol))]
            ),
            with_payload=True,
            with_vectors=False,
            limit=SCROLL_BATCH_SIZE,
            offset=offset,
        )
        if not points:
            break
        for point in points:
            payload = point.payload or {}
            feats = payload.get("features")
            target = payload.get(target_col)
            date = payload.get("date")
            if not isinstance(feats, dict) or target is None or date is None:
                continue
            records.append({"date": str(date), "features": feats, "target": float(target)})
        if offset is None:
            break

    if not records:
        raise ValueError(f"No training data found in Qdrant for symbol={symbol}")

    records.sort(key=lambda x: x["date"])
    X = pd.DataFrame([r["features"] for r in records]).apply(pd.to_numeric, errors="coerce")
    y = pd.Series([r["target"] for r in records], name=target_col)

    valid = X.notna().all(axis=1) & y.notna()
    X = X.loc[valid].reset_index(drop=True)
    y = y.loc[valid].reset_index(drop=True)

    if len(X) < 5:
        raise ValueError(f"Not enough rows for train/test split for {symbol}: {len(X)}")

    split_idx = _calculate_chronological_split_index(len(X), TRAIN_TEST_SPLIT_RATIO)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    return X_train, X_test, y_train, y_test


def _calculate_chronological_split_index(total_rows: int, ratio: float) -> int:
    desired_split_idx = math.floor(total_rows * ratio)
    min_split_idx = 1
    max_split_idx = total_rows - 1
    return max(min_split_idx, min(max_split_idx, desired_split_idx))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest 5-year historical data into Qdrant.")
    parser.add_argument("--years", type=int, default=5, help="Years of historical data to ingest")
    parser.add_argument(
        "--collection",
        type=str,
        default=TRAINING_COLLECTION,
        help="Qdrant collection used as historical training source-of-truth",
    )
    args = parser.parse_args()

    results = ingest_history(years=args.years, collection_name=args.collection)
    total = 0
    for row in results:
        print(f"{row.symbol}: {row.rows_ingested} rows")
        total += row.rows_ingested
    print(f"Total rows ingested: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
