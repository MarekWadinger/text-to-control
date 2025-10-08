from pydantic_settings import BaseSettings, Field, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
