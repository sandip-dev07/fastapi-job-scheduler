from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Job Scheduler API"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = (
        "postgresql+psycopg://jobqueue:jobqueue@localhost:5432/jobqueue"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_RETRY_BACKOFF_SECONDS: int = 5
    MAX_RETRY_BACKOFF_SECONDS: int = 300
    LOG_LEVEL: str = "INFO"


settings = Settings()
