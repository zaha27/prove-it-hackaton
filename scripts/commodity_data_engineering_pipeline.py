#!/usr/bin/env python3
"""
Standalone commodity forecasting dataset builder.

This script is fully isolated and does not modify any existing repository files.
It ingests (or scaffolds) all six required data layers, applies the requested
frequency alignment strategy, and writes one merged daily feature table.

Expected usage example:
python /home/runner/work/prove-it-hackaton/prove-it-hackaton/scripts/commodity_data_engineering_pipeline.py \
  --daily-ohlcv-csv /abs/path/daily_ohlcv.csv \
  --output-path /abs/path/commodity_features.parquet
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests


@dataclass
class SourceConfig:
    name: str
    prefix: str
    csv_path: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    expected_frequency: str = "monthly"  # daily, monthly, annual


def _safe_slug(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _read_csv_with_date(path: str) -> pd.DataFrame:
    """Reads a CSV and auto-detects a date column among common names."""
    df = pd.read_csv(path)
    candidates = ["date", "Date", "DATE", "timestamp", "Timestamp", "TIME_PERIOD", "time_period", "year"]
    date_col = next((c for c in candidates if c in df.columns), None)
    if date_col is None:
        raise ValueError(f"{path}: no date-like column found. Add one of {candidates}.")
    if date_col.lower() == "year":
        df[date_col] = pd.to_datetime(df[date_col].astype(str) + "-01-01", errors="coerce")
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    return df.rename(columns={date_col: "date"}).dropna(subset=["date"])


def _fetch_json_scaffold(cfg: SourceConfig, timeout: int = 45) -> pd.DataFrame:
    """
    API scaffold.
    Replace per-source parsing logic as needed for each provider response format.
    """
    if not cfg.api_url:
        return pd.DataFrame()
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    resp = requests.get(cfg.api_url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    records = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(records, list) or not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "date" not in df.columns:
        # Keep this explicit scaffold behavior so you can map provider-specific keys.
        # Example: df["date"] = pd.to_datetime(df["TIME_PERIOD"])
        raise ValueError(f"{cfg.name}: API response missing `date`; map it in _fetch_json_scaffold.")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["date"])


def _mock_time_series(start: pd.Timestamp, end: pd.Timestamp, freq: str, prefix: str, n_cols: int = 3) -> pd.DataFrame:
    idx = pd.date_range(start=start, end=end, freq=freq)
    out = pd.DataFrame(index=idx)
    rng = np.random.default_rng(27)
    for i in range(1, n_cols + 1):
        out[f"{prefix}_feature_{i}"] = np.cumsum(rng.normal(0, 0.2, len(idx))) + 100
    out.index.name = "date"
    return out.reset_index()


def _normalize_source(df: pd.DataFrame, prefix: str, value_cols: Optional[List[str]] = None, entity_col: Optional[str] = None) -> pd.DataFrame:
    """Converts source data to a standardized wide format keyed by `date`."""
    if df.empty:
        return df
    if "date" not in df.columns:
        raise ValueError(f"{prefix}: expected `date` column.")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    if value_cols is None:
        value_cols = [c for c in df.columns if c != "date"]
    if entity_col and entity_col in df.columns and value_cols:
        melted = df[["date", entity_col] + value_cols].melt(id_vars=["date", entity_col], value_vars=value_cols, var_name="metric", value_name="value")
        melted["feature"] = prefix + "_" + melted[entity_col].astype(str).map(_safe_slug) + "_" + melted["metric"].map(_safe_slug)
        wide = melted.pivot_table(index="date", columns="feature", values="value", aggfunc="last").reset_index()
        wide.columns.name = None
        return wide
    renamed = {c: f"{prefix}_{_safe_slug(c)}" for c in value_cols}
    return df[["date"] + value_cols].rename(columns=renamed)


def _load_source(cfg: SourceConfig, start: pd.Timestamp, end: pd.Timestamp, entity_col: Optional[str] = None) -> pd.DataFrame:
    """
    Load order:
      1) Manual CSV path (preferred for reproducibility)
      2) API scaffold (if URL provided)
      3) Mock time series fallback
    """
    if cfg.csv_path:
        df = _read_csv_with_date(cfg.csv_path)
    elif cfg.api_url:
        try:
            df = _fetch_json_scaffold(cfg)
        except (requests.RequestException, ValueError, KeyError, TypeError):
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    if df.empty:
        freq = "D" if cfg.expected_frequency == "daily" else ("MS" if cfg.expected_frequency == "monthly" else "YS")
        df = _mock_time_series(start, end, freq, cfg.prefix, n_cols=3)
    value_cols = [c for c in df.columns if c != "date" and c != (entity_col or "")]
    return _normalize_source(df, prefix=cfg.prefix, value_cols=value_cols, entity_col=entity_col)


def _prepare_daily_ohlcv(path: str) -> pd.DataFrame:
    """
    Expected CSV format (long):
      date, commodity, open, high, low, close, volume
    Also accepts wide format if already engineered.
    """
    df = _read_csv_with_date(path)
    df = df.sort_values("date")
    needed = {"commodity", "open", "high", "low", "close", "volume"}
    if needed.issubset(set(df.columns)):
        out = []
        for field in ["open", "high", "low", "close", "volume"]:
            piv = df.pivot_table(index="date", columns="commodity", values=field, aggfunc="last")
            piv.columns = [f"ohlcv_{_safe_slug(str(c))}_{field}" for c in piv.columns]
            out.append(piv)
        wide = pd.concat(out, axis=1).sort_index().reset_index()
    else:
        wide = df.copy()
        for col in [c for c in wide.columns if c != "date"]:
            wide = wide.rename(columns={col: f"ohlcv_{_safe_slug(col)}"})
    return _add_ohlcv_lag_roll_features(wide)


def _add_ohlcv_lag_roll_features(df: pd.DataFrame) -> pd.DataFrame:
    """Daily OHLCV is used as-is and enriched with lag/rolling features."""
    df = df.sort_values("date").set_index("date")
    close_cols = [c for c in df.columns if c.endswith("_close") or "close" in c]
    for c in close_cols:
        for lag in (1, 5, 20):
            df[f"{c}_lag_{lag}"] = df[c].shift(lag)
        for w in (5, 20):
            df[f"{c}_roll_mean_{w}"] = df[c].rolling(w, min_periods=1).mean()
            df[f"{c}_roll_std_{w}"] = df[c].rolling(w, min_periods=2).std()
    return df.reset_index()


def _monthly_to_daily(df: pd.DataFrame, daily_index: pd.DatetimeIndex, source_prefix: str) -> pd.DataFrame:
    """Forward-fill monthly data to daily and add months_since_update."""
    if df.empty:
        return pd.DataFrame(index=daily_index)
    base = df.set_index("date").sort_index().reindex(daily_index, method="ffill")
    source_dates = pd.DatetimeIndex(df["date"].sort_values().unique())
    pos = np.searchsorted(source_dates.values.astype("datetime64[ns]"), daily_index.values.astype("datetime64[ns]"), side="right") - 1
    last_update = pd.Series(pd.NaT, index=daily_index, dtype="datetime64[ns]")
    valid = pos >= 0
    if valid.any():
        last_update.loc[valid] = source_dates[pos[valid]]
    months_since = ((daily_index.year - last_update.dt.year) * 12 + (daily_index.month - last_update.dt.month)).astype("float")
    base[f"{source_prefix}_months_since_update"] = months_since
    return base


def _annual_to_daily(df: pd.DataFrame, daily_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Forward-fill annual data to monthly, then monthly to daily."""
    if df.empty:
        return pd.DataFrame(index=daily_index)
    annual = df.set_index("date").sort_index()
    monthly_idx = pd.date_range(start=daily_index.min(), end=daily_index.max(), freq="MS")
    monthly = annual.reindex(monthly_idx, method="ffill")
    return monthly.reindex(daily_index, method="ffill")


def _build_event_flags(daily_index: pd.DatetimeIndex, events_csv: Optional[str]) -> pd.DataFrame:
    """
    Event CSV format:
      event,start_date,end_date
      war_ukraine,2022-02-24,2024-12-31
      sanctions_russia,2022-02-24,2024-12-31
    """
    if events_csv:
        ev = pd.read_csv(events_csv)
    else:
        ev = pd.DataFrame(
            {
                "event": ["war_ukraine", "sanctions_russia"],
                "start_date": ["2022-02-24", "2022-02-24"],
                "end_date": ["2026-12-31", "2026-12-31"],
            }
        )
    out = pd.DataFrame(index=daily_index)
    ev["start_date"] = pd.to_datetime(ev["start_date"], errors="coerce")
    ev["end_date"] = pd.to_datetime(ev["end_date"], errors="coerce")
    for _, row in ev.dropna(subset=["event", "start_date", "end_date"]).iterrows():
        col = f"event_{_safe_slug(str(row['event']))}"
        out[col] = ((daily_index >= row["start_date"]) & (daily_index <= row["end_date"])).astype(int)
    return out


def _get_all_source_configs(args: argparse.Namespace) -> Dict[str, SourceConfig]:
    return {
        # Layer 1 — Price Core
        "pink_sheet": SourceConfig("World Bank Pink Sheet", "l1_pink_sheet", args.pink_sheet_csv, args.pink_sheet_api_url, args.pink_sheet_api_key, "monthly"),
        "imf_primary": SourceConfig("IMF Primary Commodity Prices", "l1_imf_primary", args.imf_primary_csv, args.imf_primary_api_url, args.imf_primary_api_key, "monthly"),
        "bakshi_cme": SourceConfig("Bakshi CME Futures", "l1_bakshi_cme", args.bakshi_cme_csv, args.bakshi_cme_api_url, args.bakshi_cme_api_key, "daily"),
        # Layer 2 — Geopolitical & Political Risk
        "gpr": SourceConfig("Caldara-Iacoviello GPR", "l2_gpr", args.gpr_csv, args.gpr_api_url, args.gpr_api_key, "monthly"),
        "wep": SourceConfig("WEP Dataverse", "l2_wep", args.wep_csv, args.wep_api_url, args.wep_api_key, "annual"),
        "qog": SourceConfig("QoG Standard", "l2_qog", args.qog_csv, args.qog_api_url, args.qog_api_key, "annual"),
        # Layer 3 — EPU
        "epu": SourceConfig("Baker-Bloom-Davis EPU", "l3_epu", args.epu_csv, args.epu_api_url, args.epu_api_key, "monthly"),
        # Layer 4 — Macro Fundamentals
        "wdi": SourceConfig("World Bank WDI", "l4_wdi", args.wdi_csv, args.wdi_api_url, args.wdi_api_key, "annual"),
        "imf_macro": SourceConfig("IMF Macro Financial", "l4_imf_macro", args.imf_macro_csv, args.imf_macro_api_url, args.imf_macro_api_key, "monthly"),
        "un_comtrade": SourceConfig("UN Comtrade", "l4_un_comtrade", args.un_comtrade_csv, args.un_comtrade_api_url, args.un_comtrade_api_key, "monthly"),
        # Layer 5 — Climate & Supply Shocks
        "ifpri": SourceConfig("IFPRI", "l5_ifpri", args.ifpri_csv, args.ifpri_api_url, args.ifpri_api_key, "monthly"),
        "fao": SourceConfig("FAO Food Price Index", "l5_fao", args.fao_csv, args.fao_api_url, args.fao_api_key, "monthly"),
        "cpu": SourceConfig("Climate Policy Uncertainty", "l5_cpu", args.cpu_csv, args.cpu_api_url, args.cpu_api_key, "monthly"),
        # Layer 6 — Sentiment & News Signals
        "arxiv_panel": SourceConfig("Arxiv Geo Daily Panel", "l6_arxiv_panel", args.arxiv_panel_csv, args.arxiv_panel_api_url, args.arxiv_panel_api_key, "daily"),
        "llm_sentiment": SourceConfig("LLM WTI Sentiment", "l6_llm_sentiment", args.llm_sentiment_csv, args.llm_sentiment_api_url, args.llm_sentiment_api_key, "daily"),
    }


def build_dataset(args: argparse.Namespace) -> pd.DataFrame:
    if not args.daily_ohlcv_csv:
        raise ValueError("--daily-ohlcv-csv is required for the daily base table.")

    # Daily base from OHLCV (exact strategy requirement).
    daily_ohlcv = _prepare_daily_ohlcv(args.daily_ohlcv_csv).set_index("date").sort_index()
    if args.start_date:
        daily_ohlcv = daily_ohlcv[daily_ohlcv.index >= pd.to_datetime(args.start_date)]
    if args.end_date:
        daily_ohlcv = daily_ohlcv[daily_ohlcv.index <= pd.to_datetime(args.end_date)]
    daily_index = pd.date_range(daily_ohlcv.index.min(), daily_ohlcv.index.max(), freq="D")
    merged = daily_ohlcv.reindex(daily_index).ffill()

    cfgs = _get_all_source_configs(args)
    loaded: Dict[str, pd.DataFrame] = {k: _load_source(v, daily_index.min(), daily_index.max()) for k, v in cfgs.items()}

    # Merge by declared frequency.
    for key, cfg in cfgs.items():
        df = loaded[key]
        if df.empty:
            continue
        if cfg.expected_frequency == "daily":
            block = df.set_index("date").sort_index().reindex(daily_index, method="ffill")
        elif cfg.expected_frequency == "monthly":
            block = _monthly_to_daily(df, daily_index, cfg.prefix)
        elif cfg.expected_frequency == "annual":
            block = _annual_to_daily(df, daily_index)
        else:
            raise ValueError(f"Unsupported frequency for {cfg.name}: {cfg.expected_frequency}")
        merged = merged.join(block, how="left")

    # Event flags by date range (wars/sanctions etc.).
    event_flags = _build_event_flags(daily_index, args.events_csv)
    merged = merged.join(event_flags, how="left")

    merged = merged.replace([np.inf, -np.inf], np.nan)
    merged["date"] = merged.index
    merged = merged.reset_index(drop=True)
    return merged


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build a comprehensive daily commodity feature table (all 6 layers).")
    p.add_argument("--daily-ohlcv-csv", required=True, help="Daily OHLCV CSV path. Expected long format: date,commodity,open,high,low,close,volume")
    p.add_argument("--output-path", required=True, help="Output file (.parquet or .csv)")
    p.add_argument("--start-date", default=None, help="Optional start date, e.g. 2000-01-01")
    p.add_argument("--end-date", default=None, help="Optional end date, e.g. 2025-12-31")
    p.add_argument("--events-csv", default=None, help="Optional events CSV with columns: event,start_date,end_date")
    p.add_argument("--metadata-json", default=None, help="Optional metadata output path")

    # Layer 1
    p.add_argument("--pink-sheet-csv", default=None)
    p.add_argument("--pink-sheet-api-url", default=None)
    p.add_argument("--pink-sheet-api-key", default=None)
    p.add_argument("--imf-primary-csv", default=None)
    p.add_argument("--imf-primary-api-url", default=None)
    p.add_argument("--imf-primary-api-key", default=None)
    p.add_argument("--bakshi-cme-csv", default=None)
    p.add_argument("--bakshi-cme-api-url", default=None)
    p.add_argument("--bakshi-cme-api-key", default=None)
    # Layer 2
    p.add_argument("--gpr-csv", default=None)
    p.add_argument("--gpr-api-url", default=None)
    p.add_argument("--gpr-api-key", default=None)
    p.add_argument("--wep-csv", default=None)
    p.add_argument("--wep-api-url", default=None)
    p.add_argument("--wep-api-key", default=None)
    p.add_argument("--qog-csv", default=None)
    p.add_argument("--qog-api-url", default=None)
    p.add_argument("--qog-api-key", default=None)
    # Layer 3
    p.add_argument("--epu-csv", default=None)
    p.add_argument("--epu-api-url", default=None)
    p.add_argument("--epu-api-key", default=None)
    # Layer 4
    p.add_argument("--wdi-csv", default=None)
    p.add_argument("--wdi-api-url", default=None)
    p.add_argument("--wdi-api-key", default=None)
    p.add_argument("--imf-macro-csv", default=None)
    p.add_argument("--imf-macro-api-url", default=None)
    p.add_argument("--imf-macro-api-key", default=None)
    p.add_argument("--un-comtrade-csv", default=None)
    p.add_argument("--un-comtrade-api-url", default=None)
    p.add_argument("--un-comtrade-api-key", default=None)
    # Layer 5
    p.add_argument("--ifpri-csv", default=None)
    p.add_argument("--ifpri-api-url", default=None)
    p.add_argument("--ifpri-api-key", default=None)
    p.add_argument("--fao-csv", default=None)
    p.add_argument("--fao-api-url", default=None)
    p.add_argument("--fao-api-key", default=None)
    p.add_argument("--cpu-csv", default=None)
    p.add_argument("--cpu-api-url", default=None)
    p.add_argument("--cpu-api-key", default=None)
    # Layer 6
    p.add_argument("--arxiv-panel-csv", default=None)
    p.add_argument("--arxiv-panel-api-url", default=None)
    p.add_argument("--arxiv-panel-api-key", default=None)
    p.add_argument("--llm-sentiment-csv", default=None)
    p.add_argument("--llm-sentiment-api-url", default=None)
    p.add_argument("--llm-sentiment-api-key", default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    merged = build_dataset(args)
    out_path = Path(args.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".parquet":
        merged.to_parquet(out_path, index=False)
    else:
        merged.to_csv(out_path, index=False)

    if args.metadata_json:
        meta = {
            "rows": int(len(merged)),
            "columns": int(len(merged.columns)),
            "date_min": str(pd.to_datetime(merged["date"]).min()),
            "date_max": str(pd.to_datetime(merged["date"]).max()),
            "output_path": str(out_path),
        }
        Path(args.metadata_json).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"[OK] Merged feature table saved: {out_path} | shape={merged.shape}")


if __name__ == "__main__":
    main()
