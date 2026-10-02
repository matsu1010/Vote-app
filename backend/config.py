from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'vote_app.db'}",
)

class Settings:
    APP_NAME = "Vote App Local Backend"
    APP_MODE = "local-first"
    DATABASE_URL = DATABASE_URL

settings = Settings()
