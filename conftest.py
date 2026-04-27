"""
Make `src` importable from tests without installing the package.

Without this, pytest's rootdir-driven sys.path doesn't include the
project root on every layout, and `from src.X import ...` fails.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
