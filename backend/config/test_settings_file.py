"""Settings for the concurrency tests (STP 1.2, NFR-15): a file SQLite test database."""

import copy
import tempfile
from pathlib import Path

from . import test_settings
from .test_settings import *  # noqa: F401,F403

# Copy, not mutate: the test runner also imports this module while discovering
# test*.py files, and must not change the in-memory settings of other runs.
DATABASES = copy.deepcopy(test_settings.DATABASES)
DATABASES["default"]["TEST"] = {
    **DATABASES["default"].get("TEST", {}),
    "NAME": str(Path(tempfile.gettempdir()) / "coffee-shop-test.sqlite3"),
}
