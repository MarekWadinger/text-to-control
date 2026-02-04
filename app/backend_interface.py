import asyncio

from src.pipeline import pipeline


def run_pipeline(prompt: str) -> str:
    """Run the pipeline in current event loop and return the result."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Use thread-safe future and wait for the result
        future = asyncio.run_coroutine_threadsafe(
            pipeline(prompt, clarification_mode="raise"),
            loop,
        )
        return future.result()
    else:
        return loop.run_until_complete(
            pipeline(prompt, clarification_mode="raise")
        )
