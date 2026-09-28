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


settings = Settings()
