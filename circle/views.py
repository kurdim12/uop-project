"""
Page views for the Raw Smith Circle app.

Five views (home, dashboard, predict_tier, predict_volume, about) plus the two
branded error handlers. The dashboard uses only the Django ORM (aggregate /
annotate / values) to build the JSON consumed by Chart.js. The prediction views
degrade gracefully when a model has not been trained yet.
"""
from __future__ import annotations

import logging

from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render

from .forms import TierPredictionForm, VolumeForecastForm
from .ml import predictor
from .models import Customer, TierPrediction, Transaction, VolumeForecast

logger = logging.getLogger("circle")

TIER_ORDER = ["bronze", "silver", "gold"]
TIER_LABELS = {"bronze": "Bronze", "silver": "Silver", "gold": "Gold"}


# --------------------------------------------------------------------------- #
# Home + About
# --------------------------------------------------------------------------- #
def home_view(request):
    """Landing page with project overview and phase summaries."""
    context = {
        "total_customers": Customer.objects.count(),
        "total_points": Transaction.objects.filter(
            transaction_type="earn"
        ).aggregate(s=Sum("points"))["s"]
        or 0,
    }
    return render(request, "circle/home.html", context)


def about_view(request):
    """Static information page summarizing all three project phases."""
    stack = [
        ("Backend", "Django 5.0"),
        ("Language", "Python 3.12"),
        ("Database", "SQLite (dev) / PostgreSQL on Render (prod)"),
        ("REST API", "Django REST Framework"),
        ("Frontend", "Django templates + Tailwind CSS (Play CDN)"),
        ("Charts", "Chart.js"),
        ("Machine learning", "scikit-learn (RandomForest), joblib"),
        ("Static files", "WhiteNoise"),
        ("Server", "Gunicorn"),
        ("Deployment", "Render (web service + managed PostgreSQL)"),
    ]
    return render(request, "circle/about.html", {"stack": stack})


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
def dashboard_payload() -> dict:
    """Build all dashboard aggregates with the ORM (shared by page + API).

    Returns:
        A dict with stats, the four chart datasets, the top-10 customers and a
        ``data_as_of`` timestamp. Everything is JSON-renderable by DRF.
    """
    total_customers = Customer.objects.count()

    total_points_issued = (
        Transaction.objects.filter(transaction_type="earn").aggregate(
            s=Sum("points")
        )["s"]
        or 0
    )
    total_redemptions = Transaction.objects.filter(
        transaction_type="redeem"
    ).count()
    total_drink_purchases = Transaction.objects.filter(
        is_drink_purchase=True
    ).count()

    # 1. Tier distribution (doughnut).
    tier_counts = {
        row["membership_tier"]: row["c"]
        for row in Customer.objects.values("membership_tier").annotate(
            c=Count("customer_id_hash")
        )
    }
    tier_chart = {
        "labels": [TIER_LABELS[t] for t in TIER_ORDER],
        "data": [tier_counts.get(t, 0) for t in TIER_ORDER],
    }

    # 2. Monthly net point flow (earned vs redeemed).
    monthly = (
        Transaction.objects.annotate(m=TruncMonth("created_at"))
        .values("m")
        .annotate(
            earned=Sum("points", filter=Q(transaction_type="earn")),
            redeemed=Sum("points", filter=Q(transaction_type="redeem")),
        )
        .order_by("m")
    )
    monthly_rows = [r for r in monthly if r["m"]]
    monthly_chart = {
        "labels": [r["m"].strftime("%Y-%m") for r in monthly_rows],
        "earned": [int(r["earned"] or 0) for r in monthly_rows],
        # Redeem points are stored negative; show the magnitude.
        "redeemed": [abs(int(r["redeemed"] or 0)) for r in monthly_rows],
    }

    # 3. Earn-source breakdown (horizontal bar).
    sources = (
        Transaction.objects.filter(transaction_type="earn")
        .values("earn_source")
        .annotate(total=Sum("points"))
        .order_by("-total")
    )
    source_chart = {
        "labels": [r["earn_source"] or "Unknown" for r in sources],
        "data": [int(r["total"] or 0) for r in sources],
    }

    # 4. Top 10 customers (HTML table).
    top_customers = list(
        Customer.objects.order_by("-total_points_earned").values(
            "customer_code",
            "membership_tier",
            "total_points_earned",
            "current_points",
        )[:10]
    )

    # 5. Daily transactions with a 7-day rolling average (line).
    daily = (
        Transaction.objects.annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(c=Count("id"))
        .order_by("d")
    )
    daily_labels, daily_counts = [], []
    for row in daily:
        if row["d"]:
            daily_labels.append(row["d"].strftime("%Y-%m-%d"))
            daily_counts.append(row["c"])
    daily_chart = {
        "labels": daily_labels,
        "counts": daily_counts,
        "rolling": _rolling_average(daily_counts, window=7),
    }

    data_as_of = Transaction.objects.aggregate(latest=Max("created_at"))["latest"]

    return {
        "has_data": total_customers > 0,
        "stats": {
            "customers": total_customers,
            "points_issued": total_points_issued,
            "redemptions": total_redemptions,
            "drink_purchases": total_drink_purchases,
        },
        "charts": {
            "tier": tier_chart,
            "monthly": monthly_chart,
            "source": source_chart,
            "daily": daily_chart,
        },
        "top_customers": top_customers,
        "data_as_of": data_as_of,
    }


def dashboard_view(request):
    """Aggregate loyalty data with the ORM and hand JSON to Chart.js."""
    payload = dashboard_payload()
    context = {
        "has_data": payload["has_data"],
        "chart_data": payload["charts"],
        "top_customers": payload["top_customers"],
        "stats": payload["stats"],
        "data_as_of": payload["data_as_of"],
    }
    return render(request, "circle/dashboard.html", context)


def _rolling_average(values: list[int], window: int = 7) -> list[float]:
    """Return a simple trailing rolling average of ``values``."""
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start : i + 1]
        out.append(round(sum(chunk) / len(chunk), 2))
    return out


# --------------------------------------------------------------------------- #
# Predictions
# --------------------------------------------------------------------------- #
def predict_tier_view(request):
    """Tier-classification form + result panel."""
    result = None
    form = TierPredictionForm(request.POST or None)
    model_ready = predictor.tier_model_available()

    if request.method == "POST" and form.is_valid():
        if not model_ready:
            form.add_error(None, "The tier model has not been trained yet.")
        else:
            features = {k: form.cleaned_data[k] for k in form.cleaned_data}
            try:
                result = predictor.predict_tier(features)
            except predictor.ModelNotTrainedError as exc:
                form.add_error(None, str(exc))
            else:
                probs = result["probabilities"]
                instance = form.save(commit=False)
                instance.predicted_tier = result["predicted_tier"]
                instance.probability_bronze = probs.get("bronze", 0.0)
                instance.probability_silver = probs.get("silver", 0.0)
                instance.probability_gold = probs.get("gold", 0.0)
                instance.confidence = result["confidence"]
                instance.save()
                logger.info(
                    "Tier prediction: %s (%.2f)",
                    result["predicted_tier"],
                    result["confidence"],
                )

    context = {
        "form": form,
        "result": result,
        "model_ready": model_ready,
        "metrics": predictor.get_tier_metrics() if model_ready else None,
        "history": TierPrediction.objects.all()[:5],
    }
    return render(request, "circle/predict_tier.html", context)


def predict_volume_view(request):
    """Daily-volume forecast form + result panel."""
    result = None
    monthly_average = None
    form = VolumeForecastForm(request.POST or None)
    model_ready = predictor.volume_model_available()

    if request.method == "POST" and form.is_valid():
        if not model_ready:
            form.add_error(None, "The volume model has not been trained yet.")
        else:
            forecast_date = form.cleaned_data["forecast_date"]
            features = {
                "temperature_max": form.cleaned_data["temperature_max"],
                "temperature_min": form.cleaned_data["temperature_min"],
                "precipitation": form.cleaned_data["precipitation"],
                "day_of_week": forecast_date.weekday(),
                "month": forecast_date.month,
                "coffee_price_usd": form.cleaned_data["coffee_price_usd"],
            }
            try:
                result = predictor.predict_volume(features)
            except predictor.ModelNotTrainedError as exc:
                form.add_error(None, str(exc))
            else:
                instance = form.save(commit=False)
                instance.day_of_week = features["day_of_week"]
                instance.month = features["month"]
                instance.predicted_points = result["predicted_points"]
                instance.predicted_transactions = result["predicted_transactions"]
                instance.recommended_reward_inventory = result[
                    "recommended_inventory"
                ]
                instance.save()
                monthly_average = _historical_daily_average(forecast_date.month)
                logger.info(
                    "Volume forecast %s: %.0f pts",
                    forecast_date,
                    result["predicted_points"],
                )

    context = {
        "form": form,
        "result": result,
        "model_ready": model_ready,
        "metrics": predictor.get_volume_metrics() if model_ready else None,
        "monthly_average": monthly_average,
        "history": VolumeForecast.objects.all()[:5],
    }
    return render(request, "circle/predict_volume.html", context)


def _historical_daily_average(month: int) -> float | None:
    """Average daily earned points for a given calendar month (or None)."""
    daily = (
        Transaction.objects.filter(transaction_type="earn", created_at__month=month)
        .annotate(d=TruncDate("created_at"))
        .values("d")
        .annotate(s=Sum("points"))
    )
    totals = [row["s"] for row in daily if row["s"] is not None]
    if not totals:
        return None
    return round(sum(totals) / len(totals), 1)


# --------------------------------------------------------------------------- #
# Error handlers (used when DEBUG=False)
# --------------------------------------------------------------------------- #
def error_404(request, exception):
    """Branded 404 page."""
    return render(request, "404.html", status=404)


def error_500(request):
    """Branded 500 page."""
    return render(request, "500.html", status=500)
