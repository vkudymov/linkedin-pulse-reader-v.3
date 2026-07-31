from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_WORKER_ROOT = Path(__file__).resolve().parents[3]
_load_dotenv(_WORKER_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str | None = None

    # LinkedIn auth (interactive)
    linkedin_auth_timeout_ms: int = 300_000
    playwright_channel: str | None = "chrome"
    playwright_user_data_dir: str = str(_WORKER_ROOT / ".playwright-profile")

    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

