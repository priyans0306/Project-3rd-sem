"""Keep all app imports in pytest isolated from the developer's SQLite file."""

import os
import tempfile


_TEST_DATABASE_DIR = tempfile.TemporaryDirectory(prefix="mail-ai-pytest-")
os.environ["MAIL_AI_DATABASE"] = os.path.join(_TEST_DATABASE_DIR.name, "test.sqlite")


def pytest_unconfigure(config):
    _TEST_DATABASE_DIR.cleanup()
