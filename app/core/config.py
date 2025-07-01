from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    EMBEDDING_SERVICE_URL: str = "http://127.0.0.1:8010"
    LLM_API_BASE:         str = "http://127.0.0.1:1234/v1"
    LLM_MODEL_NAME:       str = "meta-llama-3.1-8b-instruct"
    REQUEST_TIMEOUT:      int = 120
    EMBEDDING_SERVICE_TOKEN: str | None = None
    LLM_API_KEY:             str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")



# One object 
@lru_cache
def get_settings() -> Settings:
    """FastAPI will call this (via Depends) to inject a *single* cached
    Settings instance across the app."""
    return Settings()