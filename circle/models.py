"""
Django ORM models for the Raw Smith Circle loyalty platform.

Four models:
- Customer / Transaction : read-only mirrors of the anonymized Phase 1 tables,
  populated by the `load_data` management command and queried by the dashboard.
- TierPrediction / VolumeForecast : write models that persist every prediction
  made through the web forms or REST API, so results are auditable in /admin/.
"""
from django.db import models


class Customer(models.Model):
    """Anonymized loyalty-program member (mirror of customers.csv)."""

    TIER_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
    ]

    customer_id_hash = models.CharField(max_length=64, primary_key=True)
    customer_code = models.CharField(max_length=20, unique=True)
    membership_tier = models.CharField(
        max_length=10, choices=TIER_CHOICES, default="bronze"
    )
    current_points = models.IntegerField(default=0)
    total_points_earned = models.IntegerField(default=0)
    total_points_redeemed = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        ordering = ["-total_points_earned"]
        indexes = [models.Index(fields=["membership_tier"])]

    def __str__(self) -> str:
        return f"{self.customer_code} ({self.membership_tier})"


class Transaction(models.Model):
    """A single points event for a customer (mirror of transactions.csv)."""

    TYPE_CHOICES = [
        ("earn", "Earn"),
        ("redeem", "Redeem"),
    ]

    id = models.CharField(max_length=64, primary_key=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="transactions",
        db_column="customer_id_hash",
        to_field="customer_id_hash",
    )
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    earn_source = models.CharField(max_length=50, blank=True)
    points = models.IntegerField()
    is_drink_purchase = models.BooleanField(default=False)
    drink_category = models.CharField(max_length=50, blank=True, null=True)
    drink_price_jod = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["earn_source"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.points} pts ({self.id[:8]})"


class TierPrediction(models.Model):
    """Persisted result of a tier-classification prediction."""

    # Input features
    total_points_earned = models.IntegerField()
    transaction_count = models.IntegerField()
    drink_purchase_ratio = models.FloatField()  # 0-1
    days_since_signup = models.IntegerField()
    avg_points_per_transaction = models.FloatField()

    # Output
    predicted_tier = models.CharField(max_length=10)
    probability_bronze = models.FloatField()
    probability_silver = models.FloatField()
    probability_gold = models.FloatField()
    confidence = models.FloatField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Tier: {self.predicted_tier} ({self.confidence:.1%}) "
            f"- {self.created_at:%Y-%m-%d %H:%M}"
        )


class VolumeForecast(models.Model):
    """Persisted result of a daily-volume regression forecast."""

    # Input features
    forecast_date = models.DateField()
    temperature_max = models.FloatField()
    temperature_min = models.FloatField()
    precipitation = models.FloatField(default=0.0)
    day_of_week = models.IntegerField()  # 0 = Monday
    month = models.IntegerField()
    coffee_price_usd = models.FloatField()

    # Output
    predicted_points = models.FloatField()
    predicted_transactions = models.IntegerField()
    recommended_reward_inventory = models.IntegerField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Forecast {self.forecast_date}: "
            f"{self.predicted_points:.0f} pts / {self.predicted_transactions} txns"
        )
