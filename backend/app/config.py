import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    ENV_MODE: str = "development"

    # --- PostgreSQL Database ---
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "neurovault"
    POSTGRES_USER: str = "nv_user"
    POSTGRES_PASSWORD: str = "changeme"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- JWT / Auth Settings ---
    JWT_SECRET_KEY: str = "CHANGE_ME_run_openssl_rand_hex_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # Short-lived access token (15 min)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30         # Long-lived refresh token (30 days)

    # --- AES-256 Field Encryption ---
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = "CHANGE_ME_run_fernet_generate_key"

    # --- AI / Gemini ---
    GEMINI_API_KEY: str = ""

    # --- Storage Paths ---
    CHROMA_PERSIST_DIR: str = "/data/chromadb"
    UPLOADS_DIR: str = "/data/uploads"
    MODEL_CACHE_DIR: str = "/data/model-cache"

    # --- Feature Flags ---
    ENABLE_LOCAL_OCR: bool = True
    ENABLE_VOICE_TRANSCRIPTION: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure local storage directories exist
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)
