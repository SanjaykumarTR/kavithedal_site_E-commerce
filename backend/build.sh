#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Kavithedal Publications — Django Backend Build Script for Render
#
# Render runs this script every time a new deployment is triggered.
# Configure in Render dashboard:
#   Build Command : ./build.sh
#   Start Command : gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
# ─────────────────────────────────────────────────────────────────────────────

set -o errexit  # Exit immediately on any error

echo "─── Installing Python dependencies ───────────────────────────────────────"
pip install --upgrade pip
pip install --upgrade setuptools
pip install -r requirements.txt

echo "─── Collecting static files ──────────────────────────────────────────────"
python manage.py collectstatic --no-input

echo "─── Running database migrations ──────────────────────────────────────────"
python manage.py migrate --no-input

echo "─── Creating superuser (skipped if already exists) ──────────────────────"
# Set DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD
# as environment variables in Render dashboard to auto-create admin on first deploy.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --no-input || echo "Superuser already exists, skipping."
else
    echo "DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation."
fi

echo "─── Build complete ───────────────────────────────────────────────────────"
