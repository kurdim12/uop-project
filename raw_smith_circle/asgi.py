"""ASGI config for the Raw Smith Circle project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raw_smith_circle.settings")

application = get_asgi_application()
