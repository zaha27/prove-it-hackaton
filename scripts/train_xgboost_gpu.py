#!/usr/bin/env python3
"""
Standalone GPU-accelerated XGBoost training script for commodity forecasting.

This script is fully isolated and does not modify existing repository files.
It loads the merged daily feature table, applies a time-series split, and
trains XGBoost with GPU acceleration (`tree_method='hist'`, `device='cuda'`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost.core import XGBoostError

try:
    import cudf  # optional acceleration for loading/preprocessing
except (ImportError, ModuleNotFoundError):
    cudf = None


def _load_table(path: str, use_cudf: bool = False) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if use_cudf and cudf is not None:
        if p.suffix.lower() == ".parquet":
            gdf = cudf.read_parquet(path)
        else:
            gdf = cudf.read_csv(path)
        return gdf.to_pandas()
    if p.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _pick_default_target(df: pd.DataFrame) -> str:
    # Priority: close-like columns then first numeric column.
    candidates = [c for c in df.columns if "close" in c.lower()]
    if candidates:
        return candidates[0]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        raise ValueError("No numeric columns found to use as target.")
    return numeric_cols[0]


def _prepare_supervised(
    df: pd.DataFrame,
    target_col: str,
    date_col: str = "date",
    forecast_horizon_days: int = 1,
    drop_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    out = df.copy()
    if date_col not in out.columns:
        raise ValueError(f"Missing `{date_col}` column.")
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)
    if target_col not in out.columns:
        raise ValueError(f"Target column `{target_col}` not found.")
    out["target_future"] = out[target_col].shift(-forecast_horizon_days)
    y = out["target_future"]

    features = out.drop(columns=["target_future"])
    if drop_cols:
        features = features.drop(columns=[c for c in drop_cols if c in features.columns], errors="ignore")
    features = features.drop(columns=[date_col], errors="ignore")
    X = features.select_dtypes(include=[np.number]).copy()
    valid = ~y.isna()
    return X.loc[valid], y.loc[valid], out.loc[valid, date_col]


def _time_split(X: pd.DataFrame, y: pd.Series, dts: pd.Series, train_frac: float) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, pd.Series]:
    n = len(X)
    cut = int(n * train_frac)
    if cut <= 0 or cut >= n:
        raise ValueError(
            f"Invalid train_frac={train_frac}: must produce non-empty chronological train/test "
            f"splits (cut={cut}, samples={n})."
        )
    X_train, X_test = X.iloc[:cut], X.iloc[cut:]
    y_train, y_test = y.iloc[:cut], y.iloc[cut:]
    dt_train, dt_test = dts.iloc[:cut], dts.iloc[cut:]
    return X_train, X_test, y_train, y_test, dt_train, dt_test


def _train_gpu_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    num_boost_round: int,
    early_stopping_rounds: int,
) -> xgb.Booster:
    # Clear early failure if CUDA is unavailable, instead of a cryptic training error.
    try:
        build_info = xgb.build_info()
    except (XGBoostError, AttributeError) as exc:
        raise RuntimeError(f"Unable to query XGBoost build info: {exc}") from exc
    has_cuda = bool(
        any("cuda" in str(v).lower() for v in build_info.values())
        or "cuda" in str(build_info).lower()
    )
    if not has_cuda:
        raise RuntimeError("XGBoost CUDA support not detected; install a CUDA-enabled XGBoost build to train with device='cuda'.")

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    params = {
        "objective": "reg:squarederror",
        "eval_metric": ["rmse", "mae"],
        "tree_method": "hist",
        "device": "cuda",  # GPU acceleration required
        "max_depth": 8,
        "eta": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "min_child_weight": 1.0,
        "lambda": 1.0,
        "alpha": 0.0,
        "seed": 27,
    }
    evals = [(dtrain, "train"), (dval, "valid")]
    return xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=num_boost_round,
        evals=evals,
        early_stopping_rounds=early_stopping_rounds,
        verbose_eval=50,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train GPU-accelerated XGBoost on merged commodity features.")
    p.add_argument("--features-path", required=True, help="Merged feature table path (.parquet or .csv)")
    p.add_argument("--output-model", required=True, help="Path for XGBoost model output (e.g., model.json)")
    p.add_argument("--metrics-json", required=True, help="Path to write evaluation metrics JSON")
    p.add_argument("--date-col", default="date", help="Date column in feature table")
    p.add_argument("--target-col", default=None, help="Target column. If omitted, first close-like numeric column is used.")
    p.add_argument("--forecast-horizon-days", type=int, default=1, help="Predict target t+H from t features")
    p.add_argument("--train-frac", type=float, default=0.8, help="Train fraction for chronological split")
    p.add_argument("--num-boost-round", type=int, default=800)
    p.add_argument("--early-stopping-rounds", type=int, default=50)
    p.add_argument("--use-cudf-loader", action="store_true", help="Use cuDF for loading if available")
    p.add_argument(
        "--drop-cols",
        nargs="*",
        default=[],
        help="Optional columns to drop from features (example: leaked target proxies).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = _load_table(args.features_path, use_cudf=args.use_cudf_loader)
    target_col = args.target_col or _pick_default_target(df)
    X, y, dts = _prepare_supervised(
        df=df,
        target_col=target_col,
        date_col=args.date_col,
        forecast_horizon_days=args.forecast_horizon_days,
        drop_cols=args.drop_cols,
    )
    X_train, X_test, y_train, y_test, dt_train, dt_test = _time_split(X, y, dts, train_frac=args.train_frac)
    model = _train_gpu_model(
        X_train=X_train,
        y_train=y_train,
        X_val=X_test,
        y_val=y_test,
        num_boost_round=args.num_boost_round,
        early_stopping_rounds=args.early_stopping_rounds,
    )

    dtest = xgb.DMatrix(X_test)
    pred = model.predict(dtest)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    mae = float(mean_absolute_error(y_test, pred))
    r2 = float(r2_score(y_test, pred))

    Path(args.output_model).parent.mkdir(parents=True, exist_ok=True)
    model.save_model(args.output_model)

    metrics = {
        "target_col": target_col,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_start": str(pd.to_datetime(dt_train.min())),
        "train_end": str(pd.to_datetime(dt_train.max())),
        "test_start": str(pd.to_datetime(dt_test.min())),
        "test_end": str(pd.to_datetime(dt_test.max())),
        "forecast_horizon_days": int(args.forecast_horizon_days),
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "best_iteration": int(getattr(model, "best_iteration", -1)),
    }
    Path(args.metrics_json).write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"[OK] Model saved: {args.output_model}")
    print(f"[OK] Metrics saved: {args.metrics_json}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
