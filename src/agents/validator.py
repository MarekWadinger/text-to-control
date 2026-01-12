from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from .base import model, safe_execute_python_code


@dataclass
class ValidatorDeps:
    code: str | None = None
    results: dict[str, Any] | None = None
    logs: str | None = None


class ValidatorOutput(BaseModel):
    success: bool
    stdout: str | None = None
    error: str | None = None
    objective_name: str | None = None
    objective_value: Any | None = None


with open("src/instructions/validator.md") as f:
    validator_instructions = f.read()


class ValidatorAgent:
    """Execute and validate Pyomo models in sandbox."""

    def __init__(self):
        self.agent = Agent(
            model,
            deps_type=ValidatorDeps,
            output_type=ValidatorOutput,
            retries=3,
            instructions=validator_instructions,
        )

        @self.agent.tool()
        def run_and_validate_code(
            ctx: RunContext[ValidatorDeps],
        ) -> dict[str, Any]:
            return safe_execute_python_code(ctx.deps.code or "")
