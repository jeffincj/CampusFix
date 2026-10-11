#!/bin/sh
# Runs when the backend container starts.
set -e

# Create/update database tables.
python manage.py migrate --noinput

# Start the development server on all interfaces so Docker can expose it.
exec python manage.py runserver 0.0.0.0:8000
