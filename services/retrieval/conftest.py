"""Pytest path setup: make the service-local `app` package importable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
