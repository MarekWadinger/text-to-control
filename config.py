from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    dev_mw = "dev-mw"
    dev_ab = "dev-ab"
    prod = "prod"


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openai_api_key: str = ""
    logfire_token: str = ""
    environment: Environment = Environment.dev_mw
    model_config = SettingsConfigDict(
        env_file=(".env", ".streamlit/secrets.toml"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
