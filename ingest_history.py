#!/usr/bin/env python3
"""Ingest 5-year historical market data into Qdrant for ML training."""

from __future__ import annotations

import argparse
import hashlib
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

# Folosim maparea corectă a backend-ului
from src.data.config import config as data_config
from src.features.xgboost_features import XGBoostFeatureEngineer

TRAINING_COLLECTION = "historical_training_data"
VECTOR_SIZE = 384
TARGET_HORIZONS = (1, 3, 7, 14, 30)
UPSERT_BATCH_SIZE = 256
SCROLL_BATCH_SIZE = 1000
TRAIN_TEST_SPLIT_RATIO = 0.8
MIN_ROWS_FOR_SPLIT = 5

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
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _feature_vector(feature_values: list[float], size: int = VECTOR_SIZE) -> list[float]:
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
    digest = hashlib.sha256(f"{symbol}:{date}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & ((1 << 63) - 1)


def _prepare_symbol_dataframe(ticker: str, years: int) -> pd.DataFrame:
    try:
        hist = yf.Ticker(ticker).history(period=f"{years}y", interval="1d", auto_adjust=False)
    except Exception as exc:
        logger.warning("Failure downloading %s history: %s", ticker, exc)
        return pd.DataFrame()

    if hist.empty:
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
    qdrant = QdrantClient(url=data_config.qdrant_url)
    _ensure_collection(qdrant, collection_name)

    results: list[IngestResult] = []
    
    # AICI ESTE REPARAȚIA CHEIE: Iterăm prin commodity_symbols din backend
    for commodity_name, ticker in data_config.commodity_symbols.items():
        logger.info("Ingesting %s (%s)...", commodity_name, ticker)
        raw_df = _prepare_symbol_dataframe(ticker, years=years)
        if raw_df.empty:
            results.append(IngestResult(symbol=commodity_name, rows_ingested=0))
            continue

        feat_df, feature_cols = _engineer_training_rows(raw_df)
        if feat_df.empty:
            results.append(IngestResult(symbol=commodity_name, rows_ingested=0))
            continue

        points: list[PointStruct] = []
        for _, row in feat_df.iterrows():
            date_str = str(row["Date"])
            features = {col: _safe_float(row[col]) for col in feature_cols}
            vector = _feature_vector([features[col] for col in feature_cols])
            
            # Asociem payload-ul cu numele "GOLD", nu "GC=F"
            payload = {
                "symbol": commodity_name,
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
                    id=_row_id(commodity_name, date_str),
                    vector=vector,
                    payload=payload,
                )
            )

        for i in range(0, len(points), UPSERT_BATCH_SIZE):
            qdrant.upsert(
                collection_name=collection_name,
                points=points[i : i + UPSERT_BATCH_SIZE],
            )

        results.append(IngestResult(symbol=commodity_name, rows_ingested=len(points)))

    return results


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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