"""Settings for pytest: same as normal settings, but with a fast in-memory SQLite DB."""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast (insecure) password hashing makes tests run quicker. Test-only.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Don't let rate limits break tests that log in many times.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"auth": "10000/min"}}  # noqa: F405

# Trained models go to a temporary folder in tests (see tests/conftest.py).
