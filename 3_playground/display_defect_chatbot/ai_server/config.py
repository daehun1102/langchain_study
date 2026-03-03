# display_defect_chatbot/ai_server/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str
    postgres_user: str = "postgres"
    postgres_password: str = "1234"
    postgres_db: str = "defect_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    phoenix_collector_endpoint: str = "http://phoenix:4317"

    class Config:
        env_file = ".env"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
