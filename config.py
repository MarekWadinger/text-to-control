from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    dev = "dev"
    prod = "prod"


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openai_api_key: str = ""
    logfire_token: str = ""
    environment: Environment = Environment.dev
    model_config = SettingsConfigDict(
        env_file=(".env", ".streamlit/secrets.toml"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
