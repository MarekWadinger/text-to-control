from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    logfire_token: str = ""
    model_config = SettingsConfigDict(
        env_file=(".env", ".streamlit/secrets.toml"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
