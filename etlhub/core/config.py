import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_PROJECT_ROOT = Path(__file__).parent.parent

_env_file = os.getenv("ENV_FILE", str(_PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="allow",
    )

    host_pwd: str = "."
    logs_dir: str = "logs"
    data_dir: str = "."
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
