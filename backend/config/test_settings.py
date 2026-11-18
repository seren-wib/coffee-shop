"""Settings for the test runner (STP 1.2). Fake secrets only; CI has no repo secrets."""

import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
os.environ.setdefault("TOSS_SECRET_KEY", "test_sk_fake")

from .settings import *  # noqa: E402,F401,F403
from .settings import REST_FRAMEWORK  # noqa: E402

SECRET_KEY = "test-only-secret-key"
TOSS_SECRET_KEY = "test_sk_fake"
PAYMENTS_CLIENT = "orders.pg.FakePaymentsClient"

# Fast hashing for tests; NFR-6 tests switch back with override_settings.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Login and sign-up tests must not hit the throttle (SDD 4.1.2).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "login": "10000/min",
        "signup": "10000/min",
    },
}
