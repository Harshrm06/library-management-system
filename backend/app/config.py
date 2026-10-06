"""Application configuration loaded from environment variables.

Values are read from a ``.env`` file located in the backend project root
(the parent directory of this package).  A missing ``.env`` file is not an
error: every setting has a development-friendly default so the application
can still be imported for tests and tooling.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
ENV_FILE: Path = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    """Strongly typed application settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Library Management System API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api"
    debug: bool = False

    database_url: str = "sqlite:///./library_db.db"
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = "library_db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600

    jwt_secret: str = Field(
        default="change_me_in_production",
        min_length=8,
    )
    jwt_expiry_hours: int = 24
    algorithm: str = "HS256"
    jwt_issuer: str = "library-management-system"

    # The Vite dev server is configured for port 5173 in frontend/vite.config.js,
    # so 5173 is the origin that actually matters here; 3000 is kept only because
    # older notes in .env.example referenced it. Both the localhost and 127.0.0.1
    # spellings are listed because a browser treats them as distinct origins.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        """Return the CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def jwt_expiry_seconds(self) -> int:
        """Return the token lifetime in seconds."""
        return self.jwt_expiry_hours * 3600


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Returns:
        Settings: The application settings loaded from the environment.
    """
    return Settings()


settings: Settings = get_settings()