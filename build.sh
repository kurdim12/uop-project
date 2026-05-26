#!/usr/bin/env bash
# Render build command. Runs on every deploy.
# Order matters: install deps, gather static, apply migrations, then seed data.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Seed the database from data/*.csv only if it is still empty (idempotent).
python manage.py load_data --skip-if-exists
