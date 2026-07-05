from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]

PHASE = os.getenv("APP_ENV", "development")

ENV_FILES = [
    BASE_DIR / ".env.common",
    BASE_DIR / f".env.{PHASE}",
]

class Settings(BaseSettings):
    ENV: str = "development"

    # External services
    EMBEDDING_SERVICE_URL: str = "http://embedding-service:8080"
    CASE_SERVICE_URL: str = "http://cases:8080"

    # Request settings
    REQUEST_TIMEOUT: int = 120

    # Embedding Service auth, optional for local development
    EMBEDDING_SERVICE_TOKEN: str | None = None

    # Generation provider
    AI_PROVIDER: str = "mock"
    LLM_API_BASE: str = "http://127.0.0.1:1234/v1"
    LLM_MODEL_NAME: str = "local-model"
    LLM_API_KEY: str | None = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1000

    # AI behavior defaults
    DEFAULT_SUGGESTION_COUNT: int = 3

    # RabbitMQ
    ENABLE_RABBITMQ_CONSUMER: bool = False
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    CASE_ASSIGNED_EXCHANGE: str = "Contracts.Shared.Events:CaseAssigned"
    CASE_ASSIGNED_ROUTING_KEY: str = "case-assigned"
    CASE_ASSIGNED_QUEUE_NAME: str = "ai-service.case-assigned"

    CASE_DRAFT_GENERATED_EXCHANGE: str = "case-draft-generated"
    CASE_DRAFT_GENERATED_ROUTING_KEY: str = "case.draft.generated"

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()