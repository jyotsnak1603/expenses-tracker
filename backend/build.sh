#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Collect static files (used by the admin panel and DRF browsable API)
python manage.py collectstatic --no-input
