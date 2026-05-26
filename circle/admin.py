"""Django admin registration for all four models."""
from django.contrib import admin

from .models import Customer, TierPrediction, Transaction, VolumeForecast


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin view for the anonymized customer mirror."""

    list_display = (
        "customer_code",
        "membership_tier",
        "current_points",
        "total_points_earned",
        "total_points_redeemed",
        "created_at",
    )
    list_filter = ("membership_tier",)
    search_fields = ("customer_code", "customer_id_hash")
    ordering = ("-total_points_earned",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin view for the transaction mirror."""

    list_display = (
        "id",
        "customer",
        "transaction_type",
        "earn_source",
        "points",
        "is_drink_purchase",
        "drink_category",
        "created_at",
    )
    list_filter = ("transaction_type", "earn_source", "is_drink_purchase")
    search_fields = ("id", "customer__customer_code")
    date_hierarchy = "created_at"
    raw_id_fields = ("customer",)


@admin.register(TierPrediction)
class TierPredictionAdmin(admin.ModelAdmin):
    """Admin view for saved tier predictions."""

    list_display = (
        "predicted_tier",
        "confidence",
        "total_points_earned",
        "transaction_count",
        "created_at",
    )
    list_filter = ("predicted_tier",)
    readonly_fields = ("created_at",)


@admin.register(VolumeForecast)
class VolumeForecastAdmin(admin.ModelAdmin):
    """Admin view for saved volume forecasts."""

    list_display = (
        "forecast_date",
        "predicted_points",
        "predicted_transactions",
        "recommended_reward_inventory",
        "created_at",
    )
    list_filter = ("month", "day_of_week")
    date_hierarchy = "forecast_date"
    readonly_fields = ("created_at",)
