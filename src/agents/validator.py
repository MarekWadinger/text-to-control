from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from .base import openai_model, safe_execute_python_code
from .integrator import IntegratorOutput


@dataclass
class ValidatorDeps(IntegratorOutput):
    pass


class ObjectiveName(str, Enum):
    error = "error"
    profit = "profit"
    cost = "cost"
    labor = "labor"
    capital = "capital"
    material = "material"
    land = "land"
    water = "water"
    time = "time"
    temperature = "temperature"
    other = "other"


class ValidatorOutput(BaseModel):
    success: bool
    stdout: str | None = None
    error: str | None = None
    objective_name: ObjectiveName = ObjectiveName.other
    objective_value: Any | None = None


with open("src/instructions/validator.md") as f:
    validator_instructions = f.read()


def run_and_validate_code(
    ctx: RunContext[ValidatorDeps],
) -> dict[str, Any]:
    return safe_execute_python_code(ctx.deps.code)


class ValidatorAgent(Agent[ValidatorDeps, ValidatorOutput]):
    """Execute and validate Pyomo models in sandbox."""

    def __init__(self):
        super().__init__(
            model=openai_model,
            deps_type=ValidatorDeps,
            output_type=ValidatorOutput,
            instructions=validator_instructions,
            tools=[run_and_validate_code],
            retries=3,
        )
