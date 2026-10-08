import os
from pathlib import Path
from urllib.parse import quote
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_PROJECT_ROOT = Path(__file__).parent.parent

# The repo root .env by default. ENV_FILE overrides it, e.g. .env.debug in the
# VS Code launch configurations (local debugging only).
_env_file = os.getenv("ENV_FILE", str(_PROJECT_ROOT.parent / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="allow",
    )

    host_pwd: str = "."
    logs_dir: str = "logs"
    tracked_endpoints: str = ""
    data_dir: str = "."
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    frontend_url: str = "http://localhost:5173"
    dhis2_auth_timeout: float = 10.0
    # Comma-separated host[:port] list. Empty = every login is refused.
    dhis2_allowed_hosts: str = ""
    cookie_secure: bool = True

    @property
    def redis_url(self) -> str:
        auth = f":{quote(self.redis_password, safe='')}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
