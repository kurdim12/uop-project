"""
Django forms for the two prediction pages.

Both are ModelForms bound to the persistence models (TierPrediction /
VolumeForecast) but expose only the *input* features; the predicted outputs
are filled in by the view after the model runs.
"""
from __future__ import annotations

import datetime

from django import forms

from .models import TierPrediction, VolumeForecast

# Shared Tailwind classes for text/number inputs.
_INPUT_CLASS = (
    "w-full rounded-lg border border-muted/40 bg-white px-3 py-2 text-roast "
    "shadow-sm focus:border-caramel focus:ring-2 focus:ring-caramel/30 "
    "focus:outline-none"
)


def _num_widget(step: str = "any") -> forms.NumberInput:
    """Return a styled numeric input widget."""
    return forms.NumberInput(attrs={"class": _INPUT_CLASS, "step": step})


class TierPredictionForm(forms.ModelForm):
    """Collects the five behavioural features used to predict a tier."""

    total_points_earned = forms.IntegerField(
        min_value=0,
        max_value=5000,
        widget=_num_widget(step="1"),
        help_text="Lifetime points earned (0-5000).",
    )
    transaction_count = forms.IntegerField(
        min_value=1,
        max_value=500,
        widget=_num_widget(step="1"),
        help_text="Total number of transactions (1-500).",
    )
    drink_purchase_ratio = forms.FloatField(
        min_value=0,
        max_value=1,
        widget=_num_widget(step="0.01"),
        help_text="Share of transactions that were drink purchases (0-1).",
    )
    days_since_signup = forms.IntegerField(
        min_value=1,
        max_value=1000,
        widget=_num_widget(step="1"),
        help_text="Days since the customer joined (1-1000).",
    )
    avg_points_per_transaction = forms.FloatField(
        min_value=0,
        max_value=200,
        widget=_num_widget(step="0.1"),
        help_text="Average points earned per transaction (0-200).",
    )

    class Meta:
        model = TierPrediction
        fields = [
            "total_points_earned",
            "transaction_count",
            "drink_purchase_ratio",
            "days_since_signup",
            "avg_points_per_transaction",
        ]


class VolumeForecastForm(forms.ModelForm):
    """Collects weather + coffee-price inputs for a daily volume forecast.

    day_of_week and month are derived from forecast_date in the view, so they
    are intentionally excluded from this form.
    """

    forecast_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": _INPUT_CLASS, "type": "date"}),
        help_text="The day to forecast.",
    )
    temperature_max = forms.FloatField(
        min_value=0,
        max_value=50,
        widget=_num_widget(step="0.1"),
        help_text="Forecast daily high (0-50 C).",
    )
    temperature_min = forms.FloatField(
        min_value=-5,
        max_value=35,
        widget=_num_widget(step="0.1"),
        help_text="Forecast daily low (-5-35 C).",
    )
    precipitation = forms.FloatField(
        min_value=0,
        max_value=100,
        initial=0.0,
        widget=_num_widget(step="0.1"),
        help_text="Expected precipitation (0-100 mm).",
    )
    coffee_price_usd = forms.FloatField(
        min_value=1,
        max_value=5,
        initial=2.35,
        widget=_num_widget(step="0.01"),
        help_text="Arabica price (1-5 USD/lb).",
    )

    class Meta:
        model = VolumeForecast
        fields = [
            "forecast_date",
            "temperature_max",
            "temperature_min",
            "precipitation",
            "coffee_price_usd",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default the date to tomorrow when the form is unbound.
        if not self.is_bound and not self.initial.get("forecast_date"):
            self.initial["forecast_date"] = (
                datetime.date.today() + datetime.timedelta(days=1)
            )

    def clean(self):
        """Ensure the daily low is not above the daily high."""
        cleaned = super().clean()
        t_max = cleaned.get("temperature_max")
        t_min = cleaned.get("temperature_min")
        if t_max is not None and t_min is not None and t_min > t_max:
            self.add_error(
                "temperature_min",
                "Minimum temperature cannot exceed the maximum temperature.",
            )
        return cleaned
