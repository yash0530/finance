"""
Test configuration. Points the DB at a temporary location so tests don't
touch the user's real `~/.portfolio_intelligence/finance.db`.

Sets the env var BEFORE importing db, so the `_find_db_dir` candidate list
prefers the override path.
"""
import os
import sys
import tempfile
from pathlib import Path

# Ensure analysis/ is on sys.path so `import db` works in tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a temp DB directory by overriding the env-checked paths.
# `db.py` doesn't read an env var directly, so we monkey-patch Path.home() ?
# Cleanest: set HOME to a tempdir before db is imported.
_TMP_HOME = Path(tempfile.mkdtemp(prefix="finance_tests_"))
os.environ["HOME"] = str(_TMP_HOME)
