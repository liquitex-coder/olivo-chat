"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ACCESS_TTL: int = 900
    JWT_REFRESH_TTL: int = 2_592_000

    # Anthropic
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_PRO: str
    STRIPE_PRICE_BUSINESS: str

    # CORS / URLs
    CORS_ORIGINS: str = ""
    EMBED_BASE_URL: str = ""
    ADMIN_BASE_URL: str = ""
    API_BASE_URL: str = ""

    # Frontend (Vite) — Step 4; declared here for env_consistency with .env.example
    VITE_API_BASE_URL: str = ""


settings = Settings()
