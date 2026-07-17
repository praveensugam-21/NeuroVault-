import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    ENV_MODE: str = "development"

    # --- SQLite / PostgreSQL Database ---
    # In development, uses SQLite (DATABASE_URL=sqlite:///./iris.db in .env)
    # In production, set DATABASE_URL to a PostgreSQL URI
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "iris"
    POSTGRES_USER: str = "iris_user"
    POSTGRES_PASSWORD: str = "changeme"

    # If DATABASE_URL is explicitly set (e.g. in .env), it takes priority.
    DATABASE_URL: Optional[str] = None

    @property
    def effective_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- JWT / Auth Settings ---
    JWT_SECRET_KEY: str = "CHANGE_ME_run_openssl_rand_hex_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440      # 24 hours for dev
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- AES-256 Field Encryption ---
    ENCRYPTION_KEY: str = "CHANGE_ME_run_fernet_generate_key"

    # --- Ollama (Local LLM) Settings ---
    # Ollama is optional. If unavailable, the system uses the smart local rules engine.
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT: int = 120

    # --- Cloud AI (disabled by default for privacy) ---
    # Leave empty to keep all data 100% local.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # --- Storage Paths ---
    CHROMA_PERSIST_DIR: str = "./vector_store"
    UPLOADS_DIR: str = "./uploads"
    MODEL_CACHE_DIR: str = "./cache"

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
