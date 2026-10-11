#!/bin/sh
# Production start-up (used by the root Dockerfile and on Render).
set -e

# Create/update tables. Retry for a while in case the database is still starting.
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  python manage.py migrate --noinput && break
  echo "Database not ready (attempt $attempt), retrying in 5s..."
  sleep 5
done

# Models are trained at build time; this only saves metrics on the first start.
python manage.py train_models --if-needed

# Optional demo data: set SEED_DEMO_DATA=1 (synthetic complaints + sample rule PDFs).
if [ "$SEED_DEMO_DATA" = "1" ]; then
  python manage.py load_sample_data
  python manage.py ingest_documents
fi

# gunicorn: a production web server. WEB_CONCURRENCY = number of worker processes.
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --access-logfile -
