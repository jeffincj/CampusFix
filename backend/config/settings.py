"""
Django settings for CampusFix.

All secrets and environment-specific values come from environment
variables (loaded from a .env file). Nothing secret is hard-coded here.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root (one level above backend/), if it exists.
load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name, default="0"):
    """Read an environment variable as True/False."""
    return os.getenv(name, default).lower() in ("1", "true", "yes")


# --- Security ---------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG")
if not SECRET_KEY:
    if DEBUG:
        # Throwaway key so local dev works; never used in production.
        SECRET_KEY = "dev-only-insecure-key"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is off.")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# --- Apps -------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Our apps
    "accounts",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,  # look for templates inside each app's templates/ folder
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------------
# MySQL is the main database. SQLite is only a fallback (tests, quick demos).
if os.getenv("DB_ENGINE", "mysql") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "campusfix"),
            "USER": os.getenv("DB_USER", "campusfix"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            # utf8mb4 stores Tamil and Malayalam text correctly.
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

# --- Auth -------------------------------------------------------------------
# Our custom user model (has a "role" field). Must be set before the first migration.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:dashboard"
LOGOUT_REDIRECT_URL = "web:home"

# --- Language / time --------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic puts files here for production

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
