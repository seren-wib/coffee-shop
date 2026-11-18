"""Minimal settings for the SQLite concurrent order spike (SDD 3.1).

The DATABASES block copies SDD 9.1. SPIKE_TX_MODE switches transaction_mode
so the same code runs once with IMMEDIATE and once with DEFERRED (the default).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "spike-only-not-a-secret"
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = ["shop"]
MIDDLEWARE = []
ROOT_URLCONF = "spike.urls"
WSGI_APPLICATION = "spike.wsgi.application"

TX_MODE = os.environ.get("SPIKE_TX_MODE", "IMMEDIATE")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SPIKE_DB", BASE_DIR / "spike.sqlite3"),
        "OPTIONS": {
            "transaction_mode": TX_MODE,
            "timeout": 20,
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "Asia/Seoul"
USE_TZ = True
LANGUAGE_CODE = "ko-kr"
