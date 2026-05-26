"""
REST API endpoints (Django REST Framework).

- POST /api/predict/tier/    JSON in -> tier prediction JSON out
- POST /api/predict/volume/  JSON in -> volume forecast JSON out
- GET  /api/stats/           dashboard aggregates as JSON

Every prediction is persisted (TierPrediction / VolumeForecast) so API and
form results share the same audit trail in /admin/.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ml import predictor
from .models import TierPrediction, VolumeForecast
from .serializers import TierInputSerializer, VolumeInputSerializer
from .views import dashboard_payload


@api_view(["POST"])
def predict_tier_api(request):
    """Predict a customer's loyalty tier from behavioural features."""
    serializer = TierInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    features = serializer.validated_data

    if not predictor.tier_model_available():
        return Response(
            {"detail": "Tier model not trained yet."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    result = predictor.predict_tier(features)
    probs = result["probabilities"]
    TierPrediction.objects.create(
        total_points_earned=features["total_points_earned"],
        transaction_count=features["transaction_count"],
        drink_purchase_ratio=features["drink_purchase_ratio"],
        days_since_signup=features["days_since_signup"],
        avg_points_per_transaction=features["avg_points_per_transaction"],
        predicted_tier=result["predicted_tier"],
        probability_bronze=probs.get("bronze", 0.0),
        probability_silver=probs.get("silver", 0.0),
        probability_gold=probs.get("gold", 0.0),
        confidence=result["confidence"],
    )
    return Response(
        {
            "predicted_tier": result["predicted_tier"],
            "probabilities": probs,
            "confidence": result["confidence"],
            "recommendation": result["recommendation"],
        }
    )


@api_view(["POST"])
def predict_volume_api(request):
    """Forecast daily loyalty volume from weather + coffee price."""
    serializer = VolumeInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if not predictor.volume_model_available():
        return Response(
            {"detail": "Volume model not trained yet."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    forecast_date = data["forecast_date"]
    features = {
        "temperature_max": data["temperature_max"],
        "temperature_min": data["temperature_min"],
        "precipitation": data["precipitation"],
        "day_of_week": forecast_date.weekday(),
        "month": forecast_date.month,
        "coffee_price_usd": data["coffee_price_usd"],
    }
    result = predictor.predict_volume(features)

    VolumeForecast.objects.create(
        forecast_date=forecast_date,
        temperature_max=features["temperature_max"],
        temperature_min=features["temperature_min"],
        precipitation=features["precipitation"],
        day_of_week=features["day_of_week"],
        month=features["month"],
        coffee_price_usd=features["coffee_price_usd"],
        predicted_points=result["predicted_points"],
        predicted_transactions=result["predicted_transactions"],
        recommended_reward_inventory=result["recommended_inventory"],
    )
    return Response(
        {
            "predicted_points": round(result["predicted_points"], 1),
            "predicted_transactions": result["predicted_transactions"],
            "recommended_inventory": result["recommended_inventory"],
            "recommendation": (
                f"Plan for ~{result['predicted_transactions']} transactions; "
                f"stock about {result['recommended_inventory']} reward units."
            ),
        }
    )


@api_view(["GET"])
def stats_api(request):
    """Return the dashboard aggregates as JSON for external tooling."""
    return Response(dashboard_payload())
