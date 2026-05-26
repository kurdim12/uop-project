"""DRF serializers validating the JSON payloads for the prediction API."""
from rest_framework import serializers


class TierInputSerializer(serializers.Serializer):
    """Validates the tier-prediction request body."""

    total_points_earned = serializers.IntegerField(min_value=0, max_value=5000)
    transaction_count = serializers.IntegerField(min_value=1, max_value=500)
    drink_purchase_ratio = serializers.FloatField(min_value=0, max_value=1)
    days_since_signup = serializers.IntegerField(min_value=1, max_value=1000)
    avg_points_per_transaction = serializers.FloatField(min_value=0, max_value=200)


class VolumeInputSerializer(serializers.Serializer):
    """Validates the volume-forecast request body.

    day_of_week and month are derived from forecast_date by the view.
    """

    forecast_date = serializers.DateField()
    temperature_max = serializers.FloatField(min_value=0, max_value=50)
    temperature_min = serializers.FloatField(min_value=-5, max_value=35)
    precipitation = serializers.FloatField(min_value=0, max_value=100, default=0.0)
    coffee_price_usd = serializers.FloatField(
        min_value=1, max_value=5, default=2.35
    )

    def validate(self, attrs):
        """Reject a daily minimum above the daily maximum."""
        if attrs["temperature_min"] > attrs["temperature_max"]:
            raise serializers.ValidationError(
                "temperature_min cannot exceed temperature_max."
            )
        return attrs
