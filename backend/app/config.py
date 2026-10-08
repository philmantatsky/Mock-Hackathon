from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Settings read from environment variables, then from backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/mock_hackathon"
    phone_hmac_key: SecretStr = Field(min_length=32)
    api_token: SecretStr | None = None
    dedup_merge_threshold: float = Field(default=0.90, ge=0, le=1)
    dedup_review_threshold: float = Field(default=0.70, ge=0, le=1)
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @field_validator("api_token", mode="before")
    @classmethod
    def _empty_token_means_no_auth(cls, value: object) -> object:
        return value or None

    @model_validator(mode="after")
    def _review_threshold_not_above_merge(self) -> "Settings":
        if self.dedup_review_threshold > self.dedup_merge_threshold:
            raise ValueError("DEDUP_REVIEW_THRESHOLD must not be higher than DEDUP_MERGE_THRESHOLD")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
