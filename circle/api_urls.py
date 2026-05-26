"""URL routing for the REST API (mounted under /api/)."""
from django.urls import path

from . import api_views

app_name = "api"

urlpatterns = [
    path("predict/tier/", api_views.predict_tier_api, name="predict_tier"),
    path("predict/volume/", api_views.predict_volume_api, name="predict_volume"),
    path("stats/", api_views.stats_api, name="stats"),
]
