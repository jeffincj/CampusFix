# Backend image: Python 3.11 + Django app.
FROM python:3.11-slim

# Don't write .pyc files; print logs straight away.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python packages first (cached unless requirements.txt changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code.
COPY . .

EXPOSE 8000
# Run through "sh" so it works even when the file is not executable
# (e.g. when ./backend is mounted as a volume from Windows).
ENTRYPOINT ["sh", "entrypoint.sh"]
