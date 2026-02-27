# ai_server/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_connection: str = "postgresql+asyncpg://postgres:1234@postgres:5432/pdf_db"
    spring_base_url: str = "http://backend:8080"
    redis_host: str = "redis"
    redis_port: int = 6379
    model_name: str = "gpt-4o-mini"
    spring_api_version: str = "v1"


settings = Settings()
