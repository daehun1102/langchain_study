# display_defect_chatbot/ai_server/config.py
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    postgres_user: str = "postgres"
    postgres_password: str = "1234"
    postgres_db: str = "defect_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # ── 그래프 상태 로깅 ──────────────────────────────────────────────────
    log_graph_enabled: bool = False
    log_graph_target: Literal["console", "file", "both"] = "console"
    log_graph_file: str = "logs/graph.log"
    log_graph_level: str = "INFO"

    @property
    def pg_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def pg_sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def pg_checkpoint_url(self) -> str:
        """AsyncPostgresSaver용 psycopg3 connection string (postgresql://...)"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
