# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, SecretStr
from typing import FrozenSet, List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- Database ---
    DATABASE_URL: SecretStr
    DATABASE_URL_SYNC: SecretStr = None  # used by Alembic only

    # --- Redis ---
    REDIS_URL: SecretStr

    # --- Auth ---
    JWT_PRIVATE_KEY_PATH: str = "./secrets/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./secrets/jwt_public.pem"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: SecretStr  # for signing refresh tokens (HMAC fallback)

    # --- File Upload ---
    STORAGE_DIR: str = "./storage"
    ALLOWED_EXTENSIONS: FrozenSet[str] = frozenset({"pdf", "txt"})
    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB

    # --- AI ---
    GEMINI_API_KEY: SecretStr

    # --- App ---
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db(cls, v):
        url = v.get_secret_value()
        if "postgresql" not in url:
            raise ValueError("DATABASE_URL must be PostgreSQL")
        return v

    @property
    def jwt_private_key(self) -> str:
        with open(self.JWT_PRIVATE_KEY_PATH, "r") as f:
            return f.read()

    @property
    def jwt_public_key(self) -> str:
        with open(self.JWT_PUBLIC_KEY_PATH, "r") as f:
            return f.read()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
