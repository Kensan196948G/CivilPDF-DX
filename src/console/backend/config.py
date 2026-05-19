from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

# Cross-platform default: <user home>/civildx/uploads
# Override with UPLOAD_DIR env var or .env file.
_DEFAULT_UPLOAD_DIR = str(Path.home() / "civildx" / "uploads")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "CivilPDF-DX"
    app_version: str = "0.1.0"
    debug: bool = False

    # Development default: SQLite (cross-platform, zero config)
    # Production: set DATABASE_URL=postgresql://... in .env
    database_url: str = "sqlite:///./civilpdf_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: str = '["http://localhost:5173","http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    upload_dir: str = _DEFAULT_UPLOAD_DIR
    max_file_size_mb: int = 100

    anthropic_api_key: str = ""

    # Microsoft 365 integration — Fernet key for client_secret encryption.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    m365_fernet_key: str = ""


settings = Settings()
