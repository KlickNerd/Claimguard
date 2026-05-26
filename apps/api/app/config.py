from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    anthropic_api_key: str = ""
    anthropic_model_detection: str = "claude-sonnet-4-6"
    # Sonnet 4.6 is the default for evaluation since 2026-05-04 - the
    # quality gap to Opus 4.7 has shrunk while the knowledge base + RAG
    # picks up most of the legal lift. Set ANTHROPIC_MODEL_EVALUATION to
    # claude-opus-4-7 if you ever want to A/B for an extra-tricky case.
    anthropic_model_evaluation: str = "claude-sonnet-4-6"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_db_url: str = ""

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    kb_db_url: str = "postgresql://claimguard:claimguard@localhost:5432/claimguard"
    embedding_model: str = "intfloat/multilingual-e5-base"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Resend (Transactional E-Mails — PROJ-22 Invites, future plan mails).
    # Empty key disables sending - calls are logged + skipped instead of
    # raising, which keeps local/test runs from needing Resend creds.
    resend_api_key: str = ""
    mail_from_address: str = "noreply@claim-guard.de"
    mail_from_name: str = "ClaimGuard"

    # Public URL where the user-facing app lives, used to assemble
    # invite links. In dev it's localhost; in prod the deploy-compose
    # sets it to the canonical domain.
    public_app_url: str = "http://localhost:3000"

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
