from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PayGuard AI API"
    app_env: str = "development"
    debug: bool = True
    database_url: str = "postgresql+psycopg://payguard:payguard@localhost:5432/payguard"
    frontend_origin: str = "http://localhost:5173"

    # Payslip upload & extraction
    upload_dir: str = "storage/payslips"
    max_upload_size_mb: int = 10
    payslip_retention_days: int = 365
    ocr_enabled: bool = True

    # LangGraph verification workflow (Prompt 5)
    # The Anthropic API key itself is read directly by the anthropic SDK from the
    # standard ANTHROPIC_API_KEY env var (not PAYGUARD_-prefixed) - see backend/README.md.
    llm_enabled: bool = True
    llm_model: str = "claude-opus-5"
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 20.0
    verification_tolerance: str = "1.00"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PAYGUARD_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
