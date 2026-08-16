"""Pytest path setup: make the service-local `app` package importable."""

import os
import sys
from pathlib import Path

# torch.compile needs a C compiler that dev boxes/containers may lack.
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

sys.path.insert(0, str(Path(__file__).parent))
