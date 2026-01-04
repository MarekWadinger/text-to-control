import asyncio
from main_app import main as async_main


def run_pipeline(prompt: str, log_callback=None):
    """
    Spustenie Expert → Integrator → Validator pipeline
    """
    return asyncio.run(async_main(prompt, log_callback=log_callback))
