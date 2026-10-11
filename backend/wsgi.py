import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

# For production deployment (e.g., Gunicorn)
# gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
