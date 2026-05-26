"""WSGI config for the Raw Smith Circle project (used by Gunicorn on Render)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raw_smith_circle.settings")

application = get_wsgi_application()
