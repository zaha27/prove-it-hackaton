"""XGBoost feature engineering for multi-dimensional price analysis."""

from typing import Any

import numpy as np
import pandas as pd
from ta import momentum, trend, volatility, volume


class XGBoostFeatureEngineer:
    """Engineer high-dimensional features for XGBoost models."""

    def __init__(self) -> None:
        """Initialize feature engineer."""
        self.feature_names: list[str] = []

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer comprehensive features from OHLCV data.

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            DataFrame with engineered features
        """
        df = df.copy()

        # Price-based features
        df = self._add_price_features(df)

        # Technical indicators
        df = self._add_technical_indicators(df)

        # Volume features
        df = self._add_volume_features(df)

        # Temporal features
        df = self._add_temporal_features(df)

        # Statistical features
        df = self._add_statistical_features(df)

        # Cross-asset features (if multiple commodities)
        df = self._add_cross_features(df)

        # Pattern features
        df = self._add_pattern_features(df)

        # Store feature names
        self.feature_names = [
            c for c in df.columns
            if c not in ["Date", "Open", "High", "Low", "Close", "Volume"]
        ]

        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features."""
        # Returns
        for period in [1, 3, 5, 10, 20]:
            df[f"return_{period}d"] = df["Close"].pct_change(period) * 100

        # Log returns
        df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))

        # Price position within range
        df["price_position"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"] + 1e-10)

        # Distance from moving averages
        for ma_period in [5, 10, 20, 50, 200]:
            ma = df["Close"].rolling(ma_period).mean()
            df[f"dist_ma_{ma_period}"] = (df["Close"] - ma) / ma * 100

        # High-Low range
        df["hl_range"] = (df["High"] - df["Low"]) / df["Close"] * 100
        df["hl_range_ma5"] = df["hl_range"].rolling(5).mean()

        # Gap analysis
        df["gap"] = (df["Open"] - df["Close"].shift(1)) / df["Close"].shift(1) * 100
        df["gap_filled"] = (
            (df["Low"] <= df["Close"].shift(1)) & (df["High"] >= df["Close"].shift(1))
        ).astype(int)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features."""
        # RSI
        for period in [6, 14, 21]:
            df[f"rsi_{period}"] = momentum.rsi(df["Close"], window=period)

        # MACD
        macd = trend.MACD(df["Close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_diff"] = macd.macd_diff()

        # Bollinger Bands
        bb = volatility.BollingerBands(df["Close"])
        df["bb_high"] = bb.bollinger_hband_indicator()
        df["bb_low"] = bb.bollinger_lband_indicator()
        df["bb_width"] = bb.bollinger_wband()
        df["bb_pct"] = bb.bollinger_pband()

        # ATR (Average True Range)
        for period in [7, 14, 21]:
            df[f"atr_{period}"] = volatility.average_true_range(
                df["High"], df["Low"], df["Close"], window=period
            )
            df[f"atr_{period}_pct"] = df[f"atr_{period}"] / df["Close"] * 100

        # Stochastic
        stoch = momentum.StochasticOscillator(df["High"], df["Low"], df["Close"])
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        # CCI (Commodity Channel Index)
        df["cci"] = trend.cci(df["High"], df["Low"], df["Close"])

        # ADX (Average Directional Index)
        adx = trend.ADXIndicator(df["High"], df["Low"], df["Close"])
        df["adx"] = adx.adx()
        df["adx_pos"] = adx.adx_pos()
        df["adx_neg"] = adx.adx_neg()

        # Ichimoku Cloud
        ichimoku = trend.IchimokuIndicator(df["High"], df["Low"])
        df["ichimoku_a"] = ichimoku.ichimoku_a()
        df["ichimoku_b"] = ichimoku.ichimoku_b()
        df["ichimoku_diff"] = df["Close"] - df["ichimoku_a"]

        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        # Volume moving averages
        for period in [5, 10, 20]:
            df[f"volume_ma_{period}"] = df["Volume"].rolling(period).mean()
            df[f"volume_ratio_{period}"] = df["Volume"] / df[f"volume_ma_{period}"]

        # OBV (On Balance Volume)
        df["obv"] = volume.on_balance_volume(df["Close"], df["Volume"])
        df["obv_ma20"] = df["obv"].rolling(20).mean()

        # Volume-price trend
        df["vpt"] = volume.volume_price_trend(df["Close"], df["Volume"])

        # Money Flow Index
        df["mfi"] = volume.money_flow_index(
            df["High"], df["Low"], df["Close"], df["Volume"]
        )

        # VWAP (Volume Weighted Average Price)
        typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
        df["vwap"] = (typical_price * df["Volume"]).cumsum() / df["Volume"].cumsum()
        df["vwap_dist"] = (df["Close"] - df["vwap"]) / df["vwap"] * 100

        # Volume trend
        df["volume_trend"] = df["Volume"].rolling(10).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 10 else 0
        )

        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal/cyclical features."""
        # Parse date
        df["date"] = pd.to_datetime(df["Date"])
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_month"] = df["date"].dt.day
        df["week_of_year"] = df["date"].dt.isocalendar().week
        df["month"] = df["date"].dt.month
        df["quarter"] = df["date"].dt.quarter

        # Cyclical encoding
        df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        # Is start/end of month
        df["is_month_start"] = (df["day_of_month"] <= 5).astype(int)
        df["is_month_end"] = (df["day_of_month"] >= 25).astype(int)

        # Is weekend (for crypto, but useful for sentiment)
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Season
        df["is_summer"] = df["month"].isin([6, 7, 8]).astype(int)
        df["is_winter"] = df["month"].isin([12, 1, 2]).astype(int)

        return df

    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features."""
        returns = df["Close"].pct_change()

        # Volatility (rolling std)
        for period in [5, 10, 20, 60]:
            df[f"volatility_{period}d"] = returns.rolling(period).std() * 100

        # Skewness and Kurtosis
        for period in [10, 20]:
            df[f"skew_{period}"] = returns.rolling(period).skew()
            df[f"kurt_{period}"] = returns.rolling(period).kurt()

        # Z-score
        for period in [20, 60]:
            ma = df["Close"].rolling(period).mean()
            std = df["Close"].rolling(period).std()
            df[f"zscore_{period}"] = (df["Close"] - ma) / (std + 1e-10)

        # Percent rank
        for period in [20, 60]:
            df[f"pct_rank_{period}"] = df["Close"].rolling(period).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) == period else 0.5
            )

        # Autocorrelation
        for lag in [1, 5, 10]:
            df[f"autocorr_{lag}"] = returns.rolling(60).apply(
                lambda x: x.autocorr(lag=lag) if len(x) == 60 else 0
            )

        # Entropy (market randomness)
        for period in [10, 20]:
            df[f"entropy_{period}"] = returns.rolling(period).apply(
                lambda x: self._calculate_entropy(x.values) if len(x) == period else 0
            )

        return df

    def _add_cross_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cross-asset and derived features."""
        # Rate of change ratios
        df["roc_5_20_ratio"] = df["return_5d"] / (df["return_20d"] + 1e-10)

        # Volatility regime
        df["vol_regime"] = pd.cut(
            df["volatility_20d"],
            bins=[0, 1, 2, 5, float("inf")],
            labels=[0, 1, 2, 3],
        ).astype(float)

        # Trend strength
        df["trend_strength"] = (
            (df["return_5d"] > 0).astype(int) +
            (df["return_10d"] > 0).astype(int) +
            (df["return_20d"] > 0).astype(int)
        )

        # Momentum divergence
        df["mom_divergence"] = (
            (df["return_5d"] > 0) & (df["rsi_14"] < 50)
        ).astype(int) - (
            (df["return_5d"] < 0) & (df["rsi_14"] > 50)
        ).astype(int)

        # Support/Resistance proximity
        for period in [20, 60]:
            high_max = df["High"].rolling(period).max()
            low_min = df["Low"].rolling(period).min()
            df[f"resistance_dist_{period}"] = (high_max - df["Close"]) / df["Close"] * 100
            df[f"support_dist_{period}"] = (df["Close"] - low_min) / df["Close"] * 100

        return df

    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add pattern recognition features."""
        # Candlestick patterns
        body = abs(df["Close"] - df["Open"])
        upper_shadow = df["High"] - df[["Open", "Close"]].max(axis=1)
        lower_shadow = df[["Open", "Close"]].min(axis=1) - df["Low"]
        total_range = df["High"] - df["Low"]

        # Doji
        df["is_doji"] = (body / (total_range + 1e-10) < 0.1).astype(int)

        # Hammer/Hanging Man
        df["is_hammer"] = (
            (lower_shadow > 2 * body) & (upper_shadow < body)
        ).astype(int)

        # Engulfing (simplified)
        prev_body = body.shift(1)
        df["is_engulfing"] = (
            (body > prev_body) &
            (df["Close"] > df["Open"]) &
            (df["Close"].shift(1) < df["Open"].shift(1))
        ).astype(int)

        # Marubozu (strong trend)
        df["is_marubozu"] = (
            (body / (total_range + 1e-10) > 0.8)
        ).astype(int)

        # Consecutive up/down days
        df["consec_up"] = (
            (df["Close"] > df["Close"].shift(1)).astype(int)
            .rolling(5).sum()
        )
        df["consec_down"] = (
            (df["Close"] < df["Close"].shift(1)).astype(int)
            .rolling(5).sum()
        )

        # Breakout detection
        for period in [20, 60]:
            high_max = df["High"].rolling(period).max()
            low_min = df["Low"].rolling(period).min()
            df[f"breakout_up_{period}"] = (df["Close"] > high_max.shift(1)).astype(int)
            df[f"breakout_down_{period}"] = (df["Close"] < low_min.shift(1)).astype(int)

        return df

    @staticmethod
    def _calculate_entropy(returns: np.ndarray) -> float:
        """Calculate entropy of returns distribution."""
        if len(returns) == 0:
            return 0.0

        # Bin the returns
        hist, _ = np.histogram(returns, bins=10, density=True)
        hist = hist[hist > 0]

        if len(hist) == 0:
            return 0.0

        return -np.sum(hist * np.log(hist))

    def get_feature_importance(
        self, df: pd.DataFrame, target_col: str = "next_7d_return"
    ) -> dict[str, float]:
        """Calculate feature importance using XGBoost.

        Args:
            df: DataFrame with features and target
            target_col: Target column name

        Returns:
            Dictionary of feature importances
        """
        import xgboost as xgb
        from sklearn.model_selection import train_test_split

        # Prepare data
        feature_cols = [c for c in self.feature_names if c in df.columns]

        # Drop rows with NaN
        valid_df = df[feature_cols + [target_col]].dropna()

        if len(valid_df) < 100:
            return {"error": "Not enough data for feature importance"}

        X = valid_df[feature_cols]
        y = valid_df[target_col]

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train XGBoost
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Get feature importance
        importance = model.feature_importances_

        return dict(sorted(
            zip(feature_cols, importance),
            key=lambda x: x[1],
            reverse=True
        ))

    def prepare_xgboost_data(
        self, df: pd.DataFrame, target_horizon: int = 7
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Prepare data for XGBoost training.

        Args:
            df: DataFrame with OHLCV data
            target_horizon: Days ahead for prediction target

        Returns:
            Tuple of (features DataFrame, target Series)
        """
        # Engineer features
        df = self.engineer_features(df)

        # Create target
        df["target"] = df["Close"].shift(-target_horizon) / df["Close"] - 1

        # Select feature columns
        feature_cols = [c for c in self.feature_names if c in df.columns]

        # Drop NaN rows
        valid_df = df[feature_cols + ["target"]].dropna()

        X = valid_df[feature_cols]
        y = valid_df["target"]

        return X, y
