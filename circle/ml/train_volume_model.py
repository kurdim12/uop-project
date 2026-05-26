"""
Train the daily-volume regressor.

Goal
----
Given a day's weather, day-of-week, month and the prevailing Arabica coffee
price, predict the total loyalty points issued that day.

Pipeline : ColumnTransformer(StandardScaler + OneHotEncoder)
           -> RandomForestRegressor.
Split    : 70/30 random_state=42.
Outputs  : circle/ml/volume_model.joblib
           circle/ml/volume_model_metrics.json

Run standalone:
    python circle/ml/train_volume_model.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ML_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
# Look in data/ first, then the repo root (files are sometimes uploaded there).
_DATA_DIRS = [REPO_ROOT / "data", REPO_ROOT]
MODEL_PATH = ML_DIR / "volume_model.joblib"
METRICS_PATH = ML_DIR / "volume_model_metrics.json"


def find_data_file(name: str) -> Path:
    """Locate a data file in data/ (preferred) or the repo root."""
    for base in _DATA_DIRS:
        candidate = base / name
        if candidate.exists():
            return candidate
    return _DATA_DIRS[0] / name

NUMERIC_FEATURES = [
    "temperature_max",
    "temperature_min",
    "precipitation",
    "coffee_price_usd",
]
CATEGORICAL_FEATURES = ["day_of_week", "month"]
FEATURE_ORDER = NUMERIC_FEATURES[:3] + CATEGORICAL_FEATURES + NUMERIC_FEATURES[3:]
TARGET = "total_points"
DEFAULT_COFFEE_PRICE = 2.35

logger = logging.getLogger("train_volume_model")


def load_weather(path: Path) -> pd.DataFrame:
    """Load Amman weather into columns: date, temperature_max/min, precipitation.

    Accepts three JSON shapes: the raw Open-Meteo response ({"daily": {...}}),
    a flat dict of column->list, or a list of per-day records.
    """
    with open(path) as fh:
        raw = json.load(fh)

    if isinstance(raw, dict) and "daily" in raw:
        df = pd.DataFrame(raw["daily"]).rename(columns={"time": "date"})
    elif isinstance(raw, dict):
        df = pd.DataFrame(raw)
    else:
        df = pd.DataFrame(raw)

    rename = {
        "temperature_2m_max": "temperature_max",
        "temperature_2m_min": "temperature_min",
        "precipitation_sum": "precipitation",
    }
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    for col in ("temperature_max", "temperature_min", "precipitation"):
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill any gaps so a few missing readings don't drop whole days.
    df["precipitation"] = df["precipitation"].fillna(0.0)
    df["temperature_max"] = df["temperature_max"].fillna(df["temperature_max"].mean())
    df["temperature_min"] = df["temperature_min"].fillna(df["temperature_min"].mean())

    return df[["date", "temperature_max", "temperature_min", "precipitation"]]


def attach_coffee_price(daily: pd.DataFrame, path: Path | None) -> pd.DataFrame:
    """Add a coffee_price_usd column, merging by month as robustly as possible."""
    daily = daily.copy()
    if path is None or not path.exists():
        logger.warning("No coffee price file; using default %.2f.", DEFAULT_COFFEE_PRICE)
        daily["coffee_price_usd"] = DEFAULT_COFFEE_PRICE
        return daily

    coffee = pd.read_csv(path)
    price_col = "arabica_usd_per_lb"
    if price_col not in coffee.columns:
        # Fall back to the first numeric column if the name differs.
        numeric_cols = coffee.select_dtypes("number").columns
        price_col = numeric_cols[0] if len(numeric_cols) else None
    if price_col is None:
        daily["coffee_price_usd"] = DEFAULT_COFFEE_PRICE
        return daily

    parsed = pd.to_datetime(coffee["month"], errors="coerce")
    daily_month_str = pd.to_datetime(daily["date"]).dt.strftime("%Y-%m")

    if parsed.notna().mean() > 0.5:
        # 'month' looks like a real date -> merge on YYYY-MM.
        price_map = dict(zip(parsed.dt.strftime("%Y-%m"), coffee[price_col]))
        daily["coffee_price_usd"] = daily_month_str.map(price_map)
    else:
        # Treat 'month' as a calendar-month number, averaged across years.
        coffee["_m"] = pd.to_numeric(coffee["month"], errors="coerce")
        month_means = coffee.groupby("_m")[price_col].mean().to_dict()
        daily["coffee_price_usd"] = (
            pd.to_datetime(daily["date"]).dt.month.map(month_means)
        )

    mean_price = coffee[price_col].mean()
    fill = mean_price if pd.notna(mean_price) else DEFAULT_COFFEE_PRICE
    daily["coffee_price_usd"] = daily["coffee_price_usd"].fillna(fill)
    return daily


def build_feature_frame() -> pd.DataFrame:
    """Build the per-day feature matrix (weather is the 261-row spine)."""
    weather = load_weather(find_data_file("weather_amman.json"))

    transactions = pd.read_csv(find_data_file("transactions.csv"))
    transactions["created_date"] = pd.to_datetime(
        transactions["created_at"], errors="coerce", utc=True
    ).dt.date
    earn = transactions[transactions["transaction_type"].str.lower() == "earn"]
    daily_points = (
        earn.groupby("created_date")["points"].sum().reset_index(name=TARGET)
    )

    df = weather.merge(
        daily_points, left_on="date", right_on="created_date", how="left"
    )
    df[TARGET] = df[TARGET].fillna(0.0)

    df["day_of_week"] = pd.to_datetime(df["date"]).dt.dayofweek  # Monday=0
    df["month"] = pd.to_datetime(df["date"]).dt.month

    df = attach_coffee_price(df, find_data_file("coffee_prices_scraped.csv"))

    return df[FEATURE_ORDER + [TARGET]].copy()


def train() -> dict:
    """Train, evaluate, and serialize the volume regressor."""
    if not find_data_file("weather_amman.json").exists():
        raise FileNotFoundError(
            "Missing weather_amman.json (looked in data/ and the repo root). "
            "Place the Phase 2 enrichment files there first."
        )

    frame = build_feature_frame()
    X = frame[FEATURE_ORDER]
    y = frame[TARGET]
    logger.info("Training on %d days (%d features).", len(X), X.shape[1])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, random_state=42
    )

    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=200, max_depth=10, random_state=42
                ),
            ),
        ]
    )

    # Fit on the named DataFrame so predictor.py can pass a DataFrame back.
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    feat_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importances = pipeline.named_steps["regressor"].feature_importances_

    metrics = {
        "model": "RandomForestRegressor",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
        "residuals": {
            "y_true": [float(v) for v in y_test.tolist()],
            "y_pred": [float(v) for v in y_pred.tolist()],
        },
        "feature_importances": {
            name: float(imp) for name, imp in zip(feat_names, importances)
        },
    }

    joblib.dump(pipeline, MODEL_PATH)
    with open(METRICS_PATH, "w") as fh:
        json.dump(metrics, fh, indent=2)

    logger.info("Saved model    -> %s", MODEL_PATH)
    logger.info("Saved metrics  -> %s", METRICS_PATH)
    logger.info(
        "RMSE=%.2f  MAE=%.2f  R2=%.3f",
        metrics["rmse"],
        metrics["mae"],
        metrics["r2"],
    )
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    try:
        train()
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)
