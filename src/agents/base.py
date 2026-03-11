import google.genai.errors
import openai
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from config import Settings

# --- Model setup ---
settings = Settings()

## OpenAI Models ##
openai_provider = OpenAIProvider(api_key=settings.openai_api_key)

OPENAI_MODEL_PRIORITY = [
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.1-mini",
]
model_settings = OpenAIResponsesModelSettings(
    openai_previous_response_id="auto"
)

openai_fallback_on = (openai.RateLimitError,)
openai_model = FallbackModel(
    *[
        OpenAIChatModel(
            model, provider=openai_provider, settings=model_settings
        )
        for model in OPENAI_MODEL_PRIORITY
    ],
    fallback_on=openai_fallback_on,
)

## Gemini Models ##
google_provider = GoogleProvider(api_key=settings.gemini_api_key)

GEMINI_MODEL_PRIORITY = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]


gemini_fallback_on = (
    google.genai.errors.ClientError,
)  # Fallback on client error would usually mean we exhausted quota on specific model
gemini_model = FallbackModel(
    *[
        GoogleModel(model, provider=google_provider)
        for model in GEMINI_MODEL_PRIORITY
    ],
    fallback_on=gemini_fallback_on,
)

## Fallback Model ##
fallback_model = FallbackModel(
    openai_model,
    gemini_model,
)
