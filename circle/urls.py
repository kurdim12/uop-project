"""URL routing for the circle app (page views)."""
from django.urls import path

from . import views

app_name = "circle"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("predict/tier/", views.predict_tier_view, name="predict_tier"),
    path("predict/volume/", views.predict_volume_view, name="predict_volume"),
    path("about/", views.about_view, name="about"),
]
