from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    anthropic_api_key: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    embedding_service_url: str = "http://localhost:8080"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
