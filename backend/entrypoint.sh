#!/bin/sh
# Development start-up (docker compose "backend" service).
set -e

python manage.py migrate --noinput
python manage.py train_models --if-needed   # first start: train + evaluate the ML models

if [ "$SEED_DEMO_DATA" = "1" ]; then
  python manage.py load_sample_data          # skips itself if already loaded
  python manage.py ingest_documents
fi

# Django development server (auto-reloads when code changes).
exec python manage.py runserver 0.0.0.0:8000
