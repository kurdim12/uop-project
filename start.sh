#!/usr/bin/env sh
# Container start command for Hugging Face Spaces.
set -e

# Use the Space secret SECRET_KEY if set; otherwise generate an ephemeral one
# (fine for a demo - only admin sessions reset on restart).
export SECRET_KEY="${SECRET_KEY:-$(python -c 'import secrets; print(secrets.token_urlsafe(50))')}"

# SQLite on the container's writable layer; seed it from data/ if empty.
python manage.py migrate --noinput
python manage.py load_data --skip-if-exists

exec gunicorn raw_smith_circle.wsgi:application \
  --bind 0.0.0.0:7860 \
  --workers 2 \
  --timeout 120
