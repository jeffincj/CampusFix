# Production image: builds the React dashboard, then runs Django with gunicorn.
#   docker build -t campusfix .
#   docker run -p 8000:8000 --env-file .env campusfix

# ---- Stage 1: build the React dashboard ----
FROM node:22-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# vite.config.js writes the build to ../backend/frontend_dist/dashboard
RUN npm run build

# ---- Stage 2: Python app ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend /src/backend/frontend_dist ./frontend_dist

# Static files (Django admin, student pages, React build) and the ML models are baked into the image.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=0 DB_ENGINE=sqlite python manage.py collectstatic --noinput \
 && DJANGO_SECRET_KEY=build-only DB_ENGINE=sqlite python manage.py train_models --skip-eval

# Run as a normal user, not root.
RUN useradd --create-home campusfix && mkdir -p media && chown -R campusfix /app
USER campusfix

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz/')"
CMD ["sh", "entrypoint.prod.sh"]
