from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "CivilPDF-DX"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "postgresql://civildx:password@localhost:5432/civildx"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: str = '["http://localhost:5173","http://localhost:3000"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    upload_dir: str = "/tmp/civildx/uploads"
    max_file_size_mb: int = 100

    anthropic_api_key: str = ""

    # Microsoft 365 integration — Fernet key for client_secret encryption.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    m365_fernet_key: str = ""


settings = Settings()
