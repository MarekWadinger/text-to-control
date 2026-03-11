"""Run the Expert → Integrator → Validator pipeline."""

import logfire

from config import Settings
from src.pipeline import pipeline

# configure logfire
logfire.configure(token=Settings().logfire_token)
logfire.instrument_pydantic_ai()


async def main(prompt: str):
    result = await pipeline(prompt, clarification_mode="prompt")
    logfire.info(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        main(input("Hey there, this is Optimo. What can I help you with?"))
    )
