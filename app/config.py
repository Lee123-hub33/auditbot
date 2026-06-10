from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, SecretStr
from typing import FrozenSet, List
from pathlib import Path  # 1. Import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ... (Database, Redis stay the same) ...
    DATABASE_URL: SecretStr
    DATABASE_URL_SYNC: SecretStr = None
    REDIS_URL: SecretStr

    # 2. Update these to Path objects
    JWT_PRIVATE_KEY_PATH: Path = Path("./secrets/jwt_private.pem")
    JWT_PUBLIC_KEY_PATH: Path = Path("./secrets/jwt_public.pem")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: SecretStr

    # 2. Update this to a Path object
    STORAGE_DIR: Path = Path("./storage")
    ALLOWED_EXTENSIONS: FrozenSet[str] = frozenset({"pdf", "txt"})
    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024

    # ... (AI, App stay the same) ...
    GEMINI_API_KEY: SecretStr
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db(cls, v):
        url = v.get_secret_value()
        if "postgresql" not in url:
            raise ValueError("DATABASE_URL must be PostgreSQL")
        return v

    # 3. Use newline="" and open the Path object
    @property
    def jwt_private_key(self) -> str:
        with open(self.JWT_PRIVATE_KEY_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @property
    def jwt_public_key(self) -> str:
        with open(self.JWT_PUBLIC_KEY_PATH, "r", encoding="utf-8") as f:
            return f.read()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
