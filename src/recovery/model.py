"""
Recovery Probability Model and Explainability Engine for RecoverAI.
Uses Logistic Regression with ColumnTransformer preprocessing pipeline.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from .features import FEATURE_COLUMNS, LEAKAGE_COLUMNS


FACTOR_TRANSLATIONS = {
    "hardness_soft": "Soft failure type (temporary / retryable error)",
    "hardness_hard": "Hard failure type (permanent decline)",
    "customer_segment_high_value_repeat": "High-value repeat customer profile",
    "customer_segment_returning": "Returning customer profile",
    "customer_segment_new": "New customer profile (no prior platform history)",
    "error_code_BANK_DOWNTIME": "Temporary bank downtime (high retryability)",
    "error_code_TIMEOUT": "Payment collect / network timeout",
    "error_code_INSUFFICIENT_FUNDS": "Temporary insufficient funds",
    "error_code_TXN_LIMIT": "Transaction limit exceeded",
    "error_code_AUTH_FAILED": "3DS / authentication failure",
    "error_code_CARD_BLOCKED": "Card blocked or reported lost",
    "error_code_CARD_EXPIRED": "Card expired",
    "error_code_BAD_VPA": "Invalid UPI VPA address",
    "error_code_USER_CANCELLED": "User cancelled checkout session",
    "error_code_BANK_DECLINE": "Issuing bank decline",
    "method_upi": "Payment channel: UPI",
    "method_card": "Payment channel: Card",
    "method_netbanking": "Payment channel: Netbanking",
}


class RecoveryProbabilityModel:
    """
    Interpretable, deterministic Logistic Regression pipeline for predicting recovery probability.
    """

    def __init__(self, random_state: int = 42, c_param: float = 1.0):
        self.random_state = random_state
        self.c_param = c_param
        self.pipeline: Optional[Pipeline] = None
        self.feature_names_: List[str] = []
        self._build_pipeline()

    def _build_pipeline(self) -> None:
        numeric_features = ["amount"]
        categorical_features = ["method", "customer_segment", "error_code", "hardness"]

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ]
        )

        self.pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", LogisticRegression(random_state=self.random_state, C=self.c_param)),
            ]
        )

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Train the pipeline on observable features and extract learned feature names.
        """
        # Validate no data leakage
        for col in LEAKAGE_COLUMNS:
            if col in X.columns:
                raise ValueError(f"Data leakage detected: '{col}' must not be present in training features.")

        # Ensure only allowed feature columns
        X_clean = X[FEATURE_COLUMNS].copy()

        self.pipeline.fit(X_clean, y)

        # Extract transformed feature names
        cat_encoder = self.pipeline.named_steps["preprocessor"].named_transformers_["cat"]
        cat_names = cat_encoder.get_feature_names_out(["method", "customer_segment", "error_code", "hardness"]).tolist()
        self.feature_names_ = ["amount"] + cat_names

        return {
            "num_samples": len(X_clean),
            "num_features": len(self.feature_names_),
            "classes": self.pipeline.named_steps["classifier"].classes_.tolist(),
        }

    def _prepare_df(self, features: Union[Dict[str, Any], pd.DataFrame]) -> pd.DataFrame:
        """Sanitize and format features into a DataFrame."""
        if isinstance(features, dict):
            # Check for leakage
            for col in LEAKAGE_COLUMNS:
                if col in features:
                    raise ValueError(f"Data leakage detected: '{col}' must not be in prediction features.")
            row = {col: features.get(col) for col in FEATURE_COLUMNS}
            df = pd.DataFrame([row])
        else:
            for col in LEAKAGE_COLUMNS:
                if col in features.columns:
                    raise ValueError(f"Data leakage detected: '{col}' must not be in prediction features.")
            df = features[FEATURE_COLUMNS].copy()

        # Fill missing values safely
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["method"] = df["method"].fillna("unknown").astype(str).str.lower()
        df["customer_segment"] = df["customer_segment"].fillna("unknown").astype(str).str.lower()
        df["error_code"] = df["error_code"].fillna("UNKNOWN").astype(str).str.upper()
        df["hardness"] = df["hardness"].fillna("soft").astype(str).str.lower()
        return df

    def predict_probability(self, features: Union[Dict[str, Any], pd.DataFrame]) -> Union[float, np.ndarray]:
        """
        Predict probability of successful recovery (P in [0.0, 1.0]).
        """
        if self.pipeline is None:
            raise RuntimeError("Model pipeline has not been initialized or loaded.")

        df = self._prepare_df(features)
        probs = self.pipeline.predict_proba(df)[:, 1]

        if isinstance(features, dict) or len(df) == 1:
            return float(probs[0])
        return probs

    def explain(self, features: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        """
        Produce a deterministic, auditable feature contribution explanation.
        """
        if self.pipeline is None:
            raise RuntimeError("Model pipeline has not been initialized.")

        df = self._prepare_df(features)
        prob = float(self.pipeline.predict_proba(df)[:, 1][0])

        preprocessor = self.pipeline.named_steps["preprocessor"]
        classifier = self.pipeline.named_steps["classifier"]

        transformed = preprocessor.transform(df)
        if hasattr(transformed, "toarray"):
            dense_vec = transformed.toarray()[0]
        else:
            dense_vec = transformed[0]

        coefficients = classifier.coef_[0]
        contributions = dense_vec * coefficients

        pos_factors: List[str] = []
        neg_factors: List[str] = []

        # Sort indices by contribution magnitude
        sorted_indices = np.argsort(contributions)

        # Positive contributions (highest first)
        for idx in reversed(sorted_indices):
            val = dense_vec[idx]
            contrib = contributions[idx]
            feat_name = self.feature_names_[idx] if idx < len(self.feature_names_) else f"feature_{idx}"
            if val != 0 and contrib > 0.005:
                label = FACTOR_TRANSLATIONS.get(feat_name, feat_name)
                pos_factors.append(label)

        # Negative contributions (lowest/most negative first)
        for idx in sorted_indices:
            val = dense_vec[idx]
            contrib = contributions[idx]
            feat_name = self.feature_names_[idx] if idx < len(self.feature_names_) else f"feature_{idx}"
            if val != 0 and contrib < -0.005:
                label = FACTOR_TRANSLATIONS.get(feat_name, feat_name)
                neg_factors.append(label)

        return {
            "probability": round(prob, 4),
            "top_positive_factors": pos_factors[:top_k],
            "top_negative_factors": neg_factors[:top_k],
        }

    def save(self, filepath: Union[str, Path]) -> None:
        """Save model pipeline and feature names to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "feature_names": self.feature_names_,
                "random_state": self.random_state,
                "c_param": self.c_param,
            },
            path,
        )

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "RecoveryProbabilityModel":
        """Load serialized model pipeline from disk."""
        data = joblib.load(filepath)
        instance = cls(random_state=data.get("random_state", 42), c_param=data.get("c_param", 1.0))
        instance.pipeline = data["pipeline"]
        instance.feature_names_ = data.get("feature_names", [])
        return instance
