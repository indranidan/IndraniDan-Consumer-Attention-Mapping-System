import sys
from pathlib import Path

# Ensure project root is in sys.path so 'ai' package and sibling packages can be imported
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.main import app

__all__ = ["app"]

