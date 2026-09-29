from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARAP_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./arap.db"
    secret_key: str = "change-me-in-production-use-32+-random-bytes"
    token_minutes: int = 480
    admin_username: str = "admin"
    admin_password: str = "admin"
    seed_demo: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    # Investigation expert system — optional AI drafting of AcciMaps from report text (Manual App. E.7).
    # Off unless a key is set. Only send published final reports: protected investigation records must not leave AirNav.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_url: str = "https://api.anthropic.com/v1/messages"


settings = Settings()
