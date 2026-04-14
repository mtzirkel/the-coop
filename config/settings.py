import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-fl14i&gffwas3%j4n2(!cv3^#5v@8tl6x53u*1_z7g(zk0-9e3",
)

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_vite",
    "coop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "coop.middleware.auth.NoEgosAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
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

# Database — SQLite for dev, Postgres for production
if os.environ.get("DATABASE_URL"):
    # Parse DATABASE_URL for postgres
    import re

    m = re.match(
        r"postgres(?:ql)?://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<name>.+)",
        os.environ["DATABASE_URL"],
    )
    if m:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": m.group("name"),
                "USER": m.group("user"),
                "PASSWORD": m.group("password"),
                "HOST": m.group("host"),
                "PORT": m.group("port"),
            }
        }
    else:
        raise ValueError("Invalid DATABASE_URL format")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
_static_dirs = [BASE_DIR / "static"]
# Only include frontend/dist if it exists (requires `npm run build` in frontend/)
_frontend_dist = BASE_DIR / "frontend" / "dist"
if _frontend_dist.exists():
    _static_dirs.append(_frontend_dist)
STATICFILES_DIRS = _static_dirs
STATIC_ROOT = BASE_DIR / "staticfiles"
if not DEBUG:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# django-vite
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_host": "localhost",
        "dev_server_port": int(os.environ.get("VITE_PORT", "5176")),
        "manifest_path": BASE_DIR / "frontend" / "dist" / ".vite" / "manifest.json",
        "static_url_prefix": "",
    }
}

# NoEgos Auth
NOEGOS_AUTH_URL = os.environ.get("NOEGOS_AUTH_URL", "http://localhost:5174")
NOEGOS_AUTH_COOKIE = "noegos_auth"
NOEGOS_AUTH_LOGIN_REDIRECT = os.environ.get(
    "NOEGOS_AUTH_LOGIN_URL", "http://localhost:5174/login"
)
# Comma-separated paths that don't require auth
NOEGOS_AUTH_PUBLIC_PATHS = ["/api/health/", "/static/", "/manifest.json"]
# Dev bypass — auto-login as a fake admin user (never enable in production)
NOEGOS_AUTH_DEV_BYPASS = DEBUG
