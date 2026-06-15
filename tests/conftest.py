"""Make the repo root importable so tests can `import config` / `from src import ...`.

pytest's default import mode only adds the test file's own directory to sys.path; this
conftest at the project root guarantees the root (holding config.py and src/) is too.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
