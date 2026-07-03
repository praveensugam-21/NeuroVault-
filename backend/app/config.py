import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENV_MODE: str = "development"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen2.5:1.5b"
    
    # JWT Security Settings
    JWT_SECRET_KEY: str = "supersecretjwtkeyforhackathonauth123456"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./neurovault.db"
    
    # Storage Paths
    CHROMA_PERSIST_DIR: str = "./vector_store"
    UPLOADS_DIR: str = "./uploads"
    
    # Feature toggles
    ENABLE_LOCAL_OCR: bool = True
    ENABLE_VOICE_TRANSCRIPTION: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
