from functools import lru_cache
import os
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str | None = None
    secret_key: str = ""
    environment: str = "development"
    access_token_minutes: int = 120
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    allowed_hosts: str = "localhost,127.0.0.1,testserver,.vercel.app,.vercel.dev,.vercel.live,*"
    secure_cookies: bool = False

    @model_validator(mode="after")
    def secure_secret(self):
        if not self.secret_key:
            self.secret_key = os.getenv("SECRET_KEY", "")
        if len(self.secret_key) < 32 or self.secret_key.startswith("REPLACE_"):
            raise ValueError("SECRET_KEY must be a random string of at least 32 characters; run scripts/configure.py")
        if not self.database_url:
            self.database_url = "sqlite:///./harvestmap.db" if self.environment != "production" else ""
        if self.environment == "production" and not self.database_url:
            raise ValueError("DATABASE_URL is required in production; set a PostgreSQL URL, not SQLite.")
        if self.database_url.startswith("sqlite") and self.environment == "production":
            raise ValueError("SQLite is not supported in production on Vercel/serverless; set DATABASE_URL to PostgreSQL.")
        if self.environment == "production" and not self.secure_cookies:
            raise ValueError("SECURE_COOKIES=true is required in production")
        return self


@lru_cache
def get_settings():
    return Settings()
