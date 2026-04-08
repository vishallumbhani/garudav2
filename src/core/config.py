from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Garuda Local"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://garuda:change_this_local_password@localhost:5432/garuda"
    REDIS_URL: str = "redis://localhost:6379/0"

    GARUDA_SECRET_KEY: str = "replace_with_local_secret"
    GARUDA_ARTIFACT_SIGNING_KEY: str = "" 
    
    # JWT Settings
    JWT_SECRET_KEY: str = "replace_with_jwt_secret_at_least_32_chars_long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    LOG_LEVEL: str = "INFO"

    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    QUARANTINE_DIR: str = "./data/quarantine"
    AUDIT_LOG_PATH: str = "./logs/audit.jsonl"

    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    ALLOWED_EXTENSIONS: str = ".txt,.md,.csv,.json,.log,.pdf,.py,.js,.java,.yaml,.yml"

    DEFAULT_TENANT: str = "default"
    DEFAULT_POLICY_MODE: str = "strict"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
