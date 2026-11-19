"""Start-up checks for values read from .env (SDD 9.1). Plain functions so tests can call them."""

from django.core.exceptions import ImproperlyConfigured


def check_allowed_hosts(*, debug, hosts):
    # NFR-12: with DEBUG off Django answers 400 to every request without a host list.
    if not debug and not hosts:
        raise ImproperlyConfigured("ALLOWED_HOSTS is empty while DEBUG is off.")


def check_toss_secret_key(key):
    """True when payments can run. Only Toss test keys are allowed (NFR-13)."""
    if not key:
        return False
    if not key.startswith("test_"):
        raise ImproperlyConfigured(
            "TOSS_SECRET_KEY must be a Toss test key (test_...)."
        )
    return True
