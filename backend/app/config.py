from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/vote_app_db")

    # JWT
    secret_key: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    voter_token_expire_hours: int = int(os.getenv("VOTER_TOKEN_EXPIRE_HOURS", "24"))

    # Server
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8000"))

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost"
    ]

    # Stripe
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Argon2 defaults
    invite_code_argon2_time_cost: int = int(os.getenv("INVITE_CODE_ARGON2_TIME_COST", "3"))
    invite_code_argon2_memory_kb: int = int(os.getenv("INVITE_CODE_ARGON2_MEMORY_KB", "65536"))
    invite_code_argon2_parallelism: int = int(os.getenv("INVITE_CODE_ARGON2_PARALLELISM", "1"))

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
