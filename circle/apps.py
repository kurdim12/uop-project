"""App configuration for the circle app."""
from django.apps import AppConfig


class CircleConfig(AppConfig):
    """Configuration for the Raw Smith Circle main application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "circle"
    verbose_name = "Raw Smith Circle"
