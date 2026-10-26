import sys
import os

# Make backend/ importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import create_app  # noqa: E402

app = create_app()
