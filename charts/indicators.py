"""
charts/indicators.py — Technical indicators computed on pandas DataFrames.
# TODO: Dev2 — add more indicators (EMA, ATR, Stochastic)
"""
import pandas as pd
import numpy as np


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute RSI and return it as a Series.

    Args:
        df: DataFrame with a 'close' column.
        period: RSI lookback period (default 14).

    Returns:
        pd.Series of RSI values (0–100), same index as df.
    """
    close = df["close"].astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.rename("rsi")


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Compute MACD indicator columns.

    Args:
        df: DataFrame with a 'close' column.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        df with added columns: macd, macd_signal, macd_hist.
    """
    close = df["close"].astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    df = df.copy()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """
    Compute Bollinger Bands.

    Args:
        df: DataFrame with a 'close' column.
        period: Rolling window period (default 20).
        std_dev: Number of standard deviations for bands (default 2).

    Returns:
        df with added columns: bb_mid, bb_upper, bb_lower.
    """
    close = df["close"].astype(float)
    df = df.copy()
    df["bb_mid"] = close.rolling(window=period).mean()
    rolling_std = close.rolling(window=period).std()
    df["bb_upper"] = df["bb_mid"] + std_dev * rolling_std
    df["bb_lower"] = df["bb_mid"] - std_dev * rolling_std
    return df
