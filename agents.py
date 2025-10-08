# agents.py
from pydantic_ai import Agent
from pydantic_ai.models import GoogleModel
from pydantic_ai.providers import GoogleProvider

from config import Settings

settings = Settings()
provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel("gemini-flash-lite-latest", provider=provider)


class MyAgent:
    def __init__(self, name: str, model: str = "gemini-flash-lite-latest"):
        self.name = name
        self.agent = Agent(model)

    def solve_task(self, prompt: str) -> str:
        print(f"\n[{self.name}] is solving the task...")
        return self.agent.run(prompt)
