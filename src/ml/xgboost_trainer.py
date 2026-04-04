"""XGBoost training pipeline for commodity price prediction."""

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from qdrant_client import QdrantClient
from sklearn.model_selection import train_test_split

from config import SYMBOLS
from src.data.config import config
from src.data.vector_schema import PRICE_PATTERNS_COLLECTION

# Increase Qdrant timeout for large data loads
QDRANT_TIMEOUT = 60  # 1 minute per request
MAX_RETRIES = 3  # Retry failed requests
logger = logging.getLogger(__name__)


class XGBoostTrainer:
    """Train XGBoost models on historical patterns from Qdrant."""

    def __init__(self, model_dir: str | None = None):
        """Initialize the XGBoost trainer.

        Args:
            model_dir: Directory to save/load trained models
        """
        self.qdrant = QdrantClient(url=config.qdrant_url, timeout=QDRANT_TIMEOUT)
        self.collection_name = PRICE_PATTERNS_COLLECTION.name
        self.models: dict[str, xgb.XGBRegressor] = {}
        self.feature_importance: dict[str, dict[str, float]] = {}
        self.model_dir = Path(model_dir) if model_dir else Path("models")
        self.model_dir.mkdir(exist_ok=True)

    def load_training_data(
        self, commodity: str, target_horizon: int = 7
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Load patterns from Qdrant as training data.

        Args:
            commodity: Commodity symbol (GOLD, OIL)
            target_horizon: Days ahead for prediction target

        Returns:
            Tuple of (features DataFrame, target Series)
        """
        print(f"  Loading training data for {commodity}...")

        # Query all patterns for commodity
        target_col = f"return_{target_horizon}d"

        # Fetch data in smaller batches to avoid timeout
        all_points = []
        offset = 0
        batch_size = 500  # Smaller batches for reliability
        max_batches = 10  # Limit to avoid extremely long loading

        for batch_num in range(max_batches):
            for retry in range(MAX_RETRIES):
                try:
                    results = self.qdrant.scroll(
                        collection_name=self.collection_name,
                        scroll_filter={
                            "must": [{"key": "commodity", "match": {"value": commodity}}]
                        },
                        limit=batch_size,
                        offset=offset,
                        with_payload=True,
                    )

                    points = results[0]
                    if not points:
                        break

                    all_points.extend(points)
                    offset += len(points)

                    if len(points) < batch_size:
                        break

                    print(f"    Loaded batch {batch_num + 1}: {len(all_points)} total points...")
                    break  # Success, exit retry loop

                except Exception as e:
                    if retry < MAX_RETRIES - 1:
                        print(f"    Retry {retry + 1}/{MAX_RETRIES} after error: {e}")
                        import time
                        time.sleep(2 ** retry)  # Exponential backoff
                    else:
                        print(f"    Warning: Qdrant scroll error at batch {batch_num + 1}: {e}")
                        # Continue with what we have
                        break

            if not points or len(points) < batch_size:
                break

        print(f"    Loaded {len(all_points)} patterns from Qdrant")

        if not all_points:
            raise ValueError(f"No patterns found for {commodity}")

        # Extract features and targets
        features_list = []
        targets = []

        for point in all_points:
            payload = point.payload
            if not payload:
                continue

            # Get features
            feats = payload.get("features", {})
            if not feats:
                continue

            # Get target
            target = payload.get(target_col)
            if target is None:
                continue

            features_list.append(feats)
            targets.append(target)

        if not features_list:
            raise ValueError(f"No valid training data for {commodity}")

        # Convert to DataFrame
        X = pd.DataFrame(features_list)
        y = pd.Series(targets, name=target_col)

        # Drop rows with NaN
        valid_idx = X.notna().all(axis=1) & y.notna()
        X = X[valid_idx]
        y = y[valid_idx]

        print(f"    Valid samples: {len(X)} (features: {len(X.columns)})")

        return X, y

    def _get_model_path(self, commodity: str) -> Path:
        """Get model path for a commodity symbol."""
        if any(sep in commodity for sep in ("/", "\\", "..")):
            raise ValueError(f"Invalid commodity symbol for model path: {commodity}")
        return self.model_dir / f"xgboost_{commodity}.pkl"

    def train_model(
        self,
        commodity: str,
        target_horizon: int = 7,
        force_retrain: bool = False,
    ) -> xgb.XGBRegressor:
        """Train XGBoost model for a commodity.

        Args:
            commodity: Commodity symbol
            target_horizon: Days ahead for prediction target
            force_retrain: Whether to retrain even if model exists

        Returns:
            Trained XGBoost model
        """
        model_path = self._get_model_path(commodity)

        # Try to load existing model
        if not force_retrain and model_path.exists():
            print(f"  Loading existing model for {commodity}...")
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            self.models[commodity] = model
            return model

        print(f"  Training XGBoost model for {commodity}...")

        # Load training data
        X, y = self.load_training_data(commodity, target_horizon)

        if len(X) < 100:
            raise ValueError(f"Not enough training data for {commodity}: {len(X)} samples")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train model
        model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            early_stopping_rounds=20,
            eval_metric="rmse",
        )

        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        print(f"    Train R²: {train_score:.4f}")
        print(f"    Test R²: {test_score:.4f}")

        # Store model and feature importance
        self.models[commodity] = model
        self.feature_importance[commodity] = dict(
            zip(X.columns, model.feature_importances_)
        )

        # Save model
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        print(f"    Model saved to {model_path}")

        return model

    def train_all_models(
        self, target_horizon: int = 7, force_retrain: bool = False
    ) -> dict[str, xgb.XGBRegressor]:
        """Train models for all configured commodity symbols."""
        trained_models: dict[str, xgb.XGBRegressor] = {}
        for symbol in SYMBOLS:
            trained_models[symbol] = self.train_model(
                symbol, target_horizon=target_horizon, force_retrain=force_retrain
            )
        return trained_models

    def load_model(self, commodity: str) -> xgb.XGBRegressor:
        """Load a trained model for a commodity symbol from disk."""
        if commodity in self.models:
            return self.models[commodity]

        model_path = self._get_model_path(commodity)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found for {commodity}: {model_path.name}"
            )
        if model_path.suffix != ".pkl" or model_path.resolve().parent != self.model_dir.resolve():
            raise ValueError(f"Invalid model path for {commodity}: {model_path.name}")

        with open(model_path, "rb") as f:
            model = pickle.load(f)
        if not isinstance(model, xgb.XGBRegressor):
            raise ValueError(f"Invalid model object for {commodity}: {type(model).__name__}")
        self.models[commodity] = model
        return model

    def predict(self, commodity: str, features: dict[str, float]) -> float:
        """Make prediction for a commodity.

        Args:
            commodity: Commodity symbol
            features: Feature dictionary

        Returns:
            Predicted return
        """
        try:
            model = self.load_model(commodity)
        except FileNotFoundError:
            logger.warning(
                "Model missing for %s (%s); training on demand. Run train_all_models() to prebuild.",
                commodity,
                self._get_model_path(commodity).name,
            )
            model = self.train_model(commodity)

        # Convert features to array in correct order
        feature_names = model.get_booster().feature_names
        feature_array = np.array([[features.get(f, 0.0) for f in feature_names]])

        return float(model.predict(feature_array)[0])

    def get_feature_importance(self, commodity: str, top_n: int = 20) -> dict[str, float]:
        """Get top N most important features.

        Args:
            commodity: Commodity symbol
            top_n: Number of top features to return

        Returns:
            Dictionary of feature names to importance scores
        """
        if commodity not in self.feature_importance:
            if commodity not in self.models:
                self.train_model(commodity)
            # Recalculate from model
            model = self.models[commodity]
            self.feature_importance[commodity] = dict(
                zip(model.get_booster().feature_names, model.feature_importances_)
            )

        importance = self.feature_importance[commodity]
        sorted_importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
        )

        return sorted_importance

    def calculate_confidence(
        self, commodity: str, features: dict[str, float]
    ) -> dict[str, float]:
        """Calculate prediction confidence metrics.

        Args:
            commodity: Commodity symbol
            features: Feature dictionary

        Returns:
            Dictionary with confidence metrics
        """
        if commodity not in self.models:
            self.train_model(commodity)

        model = self.models[commodity]
        feature_names = model.get_booster().feature_names
        feature_array = np.array([[features.get(f, 0.0) for f in feature_names]])

        # Get prediction
        prediction = model.predict(feature_array)[0]

        # Get SHAP values if available
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(feature_array)
            shap_importance = np.abs(shap_values).mean()
        except Exception:
            shap_importance = 0.0

        # Calculate feature coverage (how many features are non-zero)
        non_zero_features = sum(1 for v in features.values() if v != 0)
        feature_coverage = non_zero_features / len(features) if features else 0

        # Model confidence based on feature importance alignment
        top_features = self.get_feature_importance(commodity, top_n=10)
        top_feature_values = [features.get(f, 0) for f in top_features.keys()]
        top_feature_coverage = sum(1 for v in top_feature_values if v != 0) / len(top_feature_values) if top_feature_values else 0

        # Overall confidence score (0-1)
        confidence = (
            0.4 * min(1.0, feature_coverage * 2) +  # Feature coverage
            0.4 * min(1.0, top_feature_coverage * 2) +  # Top feature coverage
            0.2 * min(1.0, shap_importance / 0.1)  # SHAP importance
        )

        return {
            "confidence": confidence,
            "feature_coverage": feature_coverage,
            "top_feature_coverage": top_feature_coverage,
            "shap_importance": shap_importance,
            "prediction": prediction,
        }

    def list_available_models(self) -> list[str]:
        """List commodities with trained models.

        Returns:
            List of commodity symbols
        """
        return list(self.models.keys())

    def predict_with_explanation(
        self, commodity: str, features: dict[str, float]
    ) -> dict[str, Any]:
        """Get prediction with full explanation.

        Args:
            commodity: Commodity symbol
            features: Feature dictionary

        Returns:
            Dictionary with prediction, confidence, and explanation
        """
        # Get prediction
        prediction = self.predict(commodity, features)

        # Get confidence metrics
        confidence_metrics = self.calculate_confidence(commodity, features)

        # Get explanation
        explanation = self.explain_prediction(commodity, features, top_n=5)

        return {
            "commodity": commodity,
            "prediction": prediction,
            "prediction_pct": prediction * 100,
            "confidence": confidence_metrics["confidence"],
            "confidence_metrics": confidence_metrics,
            "top_features": explanation["top_features"],
            "reasoning": explanation["reasoning"],
            "positive_factors": explanation["positive_factors"],
            "negative_factors": explanation["negative_factors"],
        }

    def explain_prediction(
        self, commodity: str, features: dict[str, float], top_n: int = 3
    ) -> dict[str, Any]:
        """Explain XGBoost prediction with top correlated features.

        Args:
            commodity: Commodity symbol
            features: Current feature values
            top_n: Number of top features to explain

        Returns:
            Dictionary with prediction explanation
        """
        from src.ml.feature_explainer import (
            explain_feature_value,
            get_feature_impact,
        )

        # Ensure model is loaded
        if commodity not in self.models:
            self.train_model(commodity)

        model = self.models[commodity]
        prediction = self.predict(commodity, features)

        # Get top features by importance
        top_features = self.get_feature_importance(commodity, top_n=top_n)

        # Build explanation for each top feature
        explained_features = []
        for feat_name, importance in top_features.items():
            feat_value = features.get(feat_name, 0.0)
            explanation = explain_feature_value(feat_name, feat_value)
            impact = get_feature_impact(feat_name, feat_value, importance)

            explained_features.append(
                {
                    "name": explanation["name"],
                    "technical_name": feat_name,
                    "value": feat_value,
                    "importance": importance,
                    "impact": impact,
                    "correlation": explanation["interpretation"],
                    "description": explanation["description"],
                }
            )

        # Generate auto-reasoning based on top features
        positive_factors = [f for f in explained_features if f["impact"] == "positive"]
        negative_factors = [f for f in explained_features if f["impact"] == "negative"]

        if prediction > 0.02:
            reasoning = f"Strong bullish signal ({prediction:.2%}) driven by: "
            if positive_factors:
                reasoning += f"{len(positive_factors)} positive technical factors including {positive_factors[0]['name']}."
            else:
                reasoning += "overall positive technical setup."
        elif prediction > 0.005:
            reasoning = f"Moderate bullish outlook ({prediction:.2%}) with "
            if positive_factors:
                reasoning += f"support from {positive_factors[0]['name']}."
            else:
                reasoning += "mixed technical indicators."
        elif prediction < -0.02:
            reasoning = f"Strong bearish signal ({prediction:.2%}) driven by: "
            if negative_factors:
                reasoning += f"{len(negative_factors)} negative technical factors including {negative_factors[0]['name']}."
            else:
                reasoning += "overall negative technical setup."
        elif prediction < -0.005:
            reasoning = f"Moderate bearish outlook ({prediction:.2%}) with "
            if negative_factors:
                reasoning += f"pressure from {negative_factors[0]['name']}."
            else:
                reasoning += "mixed technical indicators."
        else:
            reasoning = f"Neutral outlook ({prediction:.2%}) - technical indicators show balanced conditions."

        return {
            "prediction": prediction,
            "prediction_pct": prediction * 100,
            "top_features": explained_features,
            "reasoning": reasoning,
            "positive_factors": len(positive_factors),
            "negative_factors": len(negative_factors),
        }
