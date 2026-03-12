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
pip install -r requirements.txt

echo "─── Collecting static files ──────────────────────────────────────────────"
python manage.py collectstatic --no-input

echo "─── Running database migrations ──────────────────────────────────────────"
python manage.py migrate --no-input

echo "─── Build complete ───────────────────────────────────────────────────────"
