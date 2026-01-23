import asyncio

from main_app import main as async_main


def run_pipeline(prompt: str, api_key: str = None) -> str:
    """Pomoc ."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Použijeme thread-safe future a počkáme na výsledok
        future = asyncio.run_coroutine_threadsafe(async_main(prompt), loop)
        return future.result()
    else:
        return loop.run_until_complete(async_main(prompt))
