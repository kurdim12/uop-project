"""
Train the membership-tier classifier.

Goal
----
Given a customer's behavioural features, predict their loyalty tier
(bronze / silver / gold).

Pipeline : StandardScaler -> RandomForestClassifier (balanced).
Split    : 70/30 stratified, random_state=42.
Outputs  : circle/ml/tier_model.joblib
           circle/ml/tier_model_metrics.json

Run standalone:
    python circle/ml/train_tier_model.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ML_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
# Look in data/ first, then the repo root (files are sometimes uploaded there).
_DATA_DIRS = [REPO_ROOT / "data", REPO_ROOT]
MODEL_PATH = ML_DIR / "tier_model.joblib"
METRICS_PATH = ML_DIR / "tier_model_metrics.json"


def find_data_file(name: str) -> Path:
    """Locate a data file in data/ (preferred) or the repo root."""
    for base in _DATA_DIRS:
        candidate = base / name
        if candidate.exists():
            return candidate
    return _DATA_DIRS[0] / name

# Feature column order — MUST match circle/ml/predictor.py:predict_tier.
FEATURE_ORDER = [
    "total_points_earned",
    "transaction_count",
    "drink_purchase_ratio",
    "days_since_signup",
    "avg_points_per_transaction",
]
TARGET = "membership_tier"

logger = logging.getLogger("train_tier_model")


def build_feature_frame() -> pd.DataFrame:
    """Build the per-customer feature matrix from the anonymized CSVs.

    Returns:
        DataFrame with FEATURE_ORDER columns plus the TARGET column.
    """
    customers = pd.read_csv(find_data_file("customers.csv"))
    transactions = pd.read_csv(find_data_file("transactions.csv"))

    # Per-customer transaction aggregates.
    transactions["is_drink_purchase"] = (
        transactions["is_drink_purchase"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes", "t"])
    )
    agg = transactions.groupby("customer_id_hash").agg(
        transaction_count=("id", "count"),
        drink_count=("is_drink_purchase", "sum"),
    )

    df = customers.merge(agg, on="customer_id_hash", how="left")
    df["transaction_count"] = df["transaction_count"].fillna(0).astype(int)
    df["drink_count"] = df["drink_count"].fillna(0).astype(int)

    # Derived features (guard against division by zero).
    df["drink_purchase_ratio"] = np.where(
        df["transaction_count"] > 0,
        df["drink_count"] / df["transaction_count"],
        0.0,
    )
    df["avg_points_per_transaction"] = np.where(
        df["transaction_count"] > 0,
        df["total_points_earned"] / df["transaction_count"],
        0.0,
    )

    created = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    now = pd.Timestamp.now(tz="UTC")
    df["days_since_signup"] = (
        (now - created).dt.days.fillna(0).clip(lower=0).astype(int)
    )

    df[TARGET] = df[TARGET].astype(str).str.strip().str.lower()
    df = df[df[TARGET].isin(["bronze", "silver", "gold"])]

    return df[FEATURE_ORDER + [TARGET]].copy()


def train() -> dict:
    """Train, evaluate, and serialize the tier classifier.

    Returns:
        The metrics dictionary that was written to disk.
    """
    customers_path = find_data_file("customers.csv")
    if not customers_path.exists():
        raise FileNotFoundError(
            "Missing customers.csv (looked in data/ and the repo root). "
            "Place the anonymized Phase 1 CSVs there first."
        )

    frame = build_feature_frame()
    X = frame[FEATURE_ORDER]
    y = frame[TARGET]
    logger.info("Training on %d customers (%d features).", len(X), X.shape[1])
    logger.info("Class balance:\n%s", y.value_counts().to_string())

    # Stratify only when every class has at least two samples.
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=stratify
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    # Fit on raw arrays (no column names) so predictor.py can call the model
    # with a plain numpy array without triggering feature-name warnings.
    pipeline.fit(X_train.values, y_train.values)
    y_pred = pipeline.predict(X_test.values)

    classes = sorted(y.unique().tolist())
    importances = pipeline.named_steps["classifier"].feature_importances_

    metrics = {
        "model": "RandomForestClassifier",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "classes": classes,
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_weighted": float(f1_score(y_test, y_pred, average="weighted")),
        "classification_report": classification_report(
            y_test, y_pred, output_dict=True, zero_division=0
        ),
        "confusion_matrix": {
            "labels": classes,
            "matrix": confusion_matrix(y_test, y_pred, labels=classes).tolist(),
        },
        "feature_importances": {
            feat: float(imp) for feat, imp in zip(FEATURE_ORDER, importances)
        },
    }

    joblib.dump(pipeline, MODEL_PATH)
    with open(METRICS_PATH, "w") as fh:
        json.dump(metrics, fh, indent=2)

    logger.info("Saved model    -> %s", MODEL_PATH)
    logger.info("Saved metrics  -> %s", METRICS_PATH)
    logger.info(
        "Accuracy=%.3f  F1(weighted)=%.3f",
        metrics["accuracy"],
        metrics["f1_weighted"],
    )
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    try:
        train()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)
