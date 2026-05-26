"""
Inference helpers: load the serialized models once and expose predict fns.

Used by both the Django views and the REST API. Models are loaded lazily on
first use and then cached at module level. If a model has not been trained yet
(no .joblib on disk), ``ModelNotTrainedError`` is raised so callers can show a
friendly "train the model first" message instead of crashing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ML_DIR = Path(__file__).resolve().parent

TIER_MODEL_PATH = ML_DIR / "tier_model.joblib"
TIER_METRICS_PATH = ML_DIR / "tier_model_metrics.json"
VOLUME_MODEL_PATH = ML_DIR / "volume_model.joblib"
VOLUME_METRICS_PATH = ML_DIR / "volume_model_metrics.json"

# Feature order — MUST match circle/ml/train_tier_model.py:FEATURE_ORDER.
TIER_FEATURE_ORDER = [
    "total_points_earned",
    "transaction_count",
    "drink_purchase_ratio",
    "days_since_signup",
    "avg_points_per_transaction",
]

# Average points per transaction (Phase 1 finding) used to convert a predicted
# points total into an approximate transaction count.
AVG_POINTS_PER_TXN = 17.7

_tier_model = None
_volume_model = None
_tier_metrics: dict | None = None
_volume_metrics: dict | None = None


class ModelNotTrainedError(RuntimeError):
    """Raised when a prediction is requested before the model is trained."""


def tier_model_available() -> bool:
    """Return True if the tier model has been trained and serialized."""
    return TIER_MODEL_PATH.exists()


def volume_model_available() -> bool:
    """Return True if the volume model has been trained and serialized."""
    return VOLUME_MODEL_PATH.exists()


def _load_tier():
    """Load (and cache) the tier model and its metrics."""
    global _tier_model, _tier_metrics
    if _tier_model is None:
        if not TIER_MODEL_PATH.exists():
            raise ModelNotTrainedError(
                "Tier model not found. Run: python circle/ml/train_tier_model.py"
            )
        _tier_model = joblib.load(TIER_MODEL_PATH)
        if TIER_METRICS_PATH.exists():
            with open(TIER_METRICS_PATH) as fh:
                _tier_metrics = json.load(fh)
    return _tier_model, _tier_metrics


def _load_volume():
    """Load (and cache) the volume model and its metrics."""
    global _volume_model, _volume_metrics
    if _volume_model is None:
        if not VOLUME_MODEL_PATH.exists():
            raise ModelNotTrainedError(
                "Volume model not found. Run: python circle/ml/train_volume_model.py"
            )
        _volume_model = joblib.load(VOLUME_MODEL_PATH)
        if VOLUME_METRICS_PATH.exists():
            with open(VOLUME_METRICS_PATH) as fh:
                _volume_metrics = json.load(fh)
    return _volume_model, _volume_metrics


def predict_tier(features: dict[str, float]) -> dict[str, Any]:
    """Predict a customer's loyalty tier.

    Args:
        features: Keys total_points_earned, transaction_count,
            drink_purchase_ratio, days_since_signup,
            avg_points_per_transaction.

    Returns:
        Dict with predicted_tier, probabilities (per class), confidence
        (max probability) and a business recommendation string.
    """
    model, _ = _load_tier()
    X = np.array([[float(features[name]) for name in TIER_FEATURE_ORDER]])

    pred = str(model.predict(X)[0])
    probs = model.predict_proba(X)[0]
    classes = model.classes_
    prob_dict = {str(cls): float(p) for cls, p in zip(classes, probs)}
    # Guarantee all three tiers are present so callers/templates never miss a key.
    for tier in ("bronze", "silver", "gold"):
        prob_dict.setdefault(tier, 0.0)
    confidence = float(max(probs))

    if pred == "gold":
        rec = "VIP customer. Offer exclusive Gold rewards and personalized outreach."
    elif pred == "silver":
        rec = "Active customer. Promote Silver-tier rewards to drive engagement."
    elif prob_dict.get("silver", 0) > 0.25:
        rec = "Bronze with upgrade potential. Send 'almost Silver' nudge campaign."
    else:
        rec = "Early-stage Bronze. Send welcome bonus and onboarding emails."

    return {
        "predicted_tier": pred,
        "probabilities": prob_dict,
        "confidence": confidence,
        "recommendation": rec,
    }


def predict_volume(features: dict[str, float]) -> dict[str, Any]:
    """Forecast daily loyalty volume.

    Args:
        features: Keys temperature_max, temperature_min, precipitation,
            day_of_week, month, coffee_price_usd.

    Returns:
        Dict with predicted_points, predicted_transactions and a recommended
        reward-inventory level.
    """
    import pandas as pd

    model, _ = _load_volume()
    X = pd.DataFrame(
        [
            {
                "temperature_max": float(features["temperature_max"]),
                "temperature_min": float(features["temperature_min"]),
                "precipitation": float(features["precipitation"]),
                "day_of_week": int(features["day_of_week"]),
                "month": int(features["month"]),
                "coffee_price_usd": float(features["coffee_price_usd"]),
            }
        ]
    )

    pred_points = max(0.0, float(model.predict(X)[0]))
    pred_txns = max(1, int(round(pred_points / AVG_POINTS_PER_TXN)))
    recommended_inv = max(5, int(pred_points / 100))

    return {
        "predicted_points": pred_points,
        "predicted_transactions": pred_txns,
        "recommended_inventory": recommended_inv,
    }


def get_tier_metrics() -> dict | None:
    """Return the saved tier-model evaluation metrics (or None)."""
    _, metrics = _load_tier()
    return metrics


def get_volume_metrics() -> dict | None:
    """Return the saved volume-model evaluation metrics (or None)."""
    _, metrics = _load_volume()
    return metrics
