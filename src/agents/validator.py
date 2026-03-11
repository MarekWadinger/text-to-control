import asyncio
import os
import subprocess
import tempfile
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .base import openai_model
from .integrator import ALLOWED_PACKAGES, IntegratorOutput


class ValidatorDeps(IntegratorOutput): ...


class ObjectiveName(StrEnum):
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
    success: bool = Field(
        default=False,
        description="Whether the code executed successfully.",
    )
    stdout: str | None = Field(
        default=None,
        description="The standard output of the code execution.",
    )
    error: str | None = Field(
        default=None,
        description="The error message if the code execution failed.",
    )
    objective_name: ObjectiveName = Field(
        default=ObjectiveName.other,
        description="The name of the objective function.",
    )
    objective_value: Any | None = Field(
        default=None,
        description="The value of the objective function.",
    )


with open("src/instructions/validator.md") as f:
    validator_instructions = f.read()

DOCKER_IMAGE = "text-to-control-validator"


def _normalise_dep(dep: str) -> str:
    """Strip version specifiers and extras: 'numpy>=1.0[all]' -> 'numpy'."""
    import re

    return re.split(r"[><=!\[;]", dep.strip())[0].lower()


async def execute_in_docker(
    code: str, dependencies: list[str]
) -> dict[str, Any]:
    """Execute code in an isolated Docker container with pre-installed solvers."""
    unknown = {_normalise_dep(d) for d in dependencies} - ALLOWED_PACKAGES
    if unknown:
        return {
            "stdout": None,
            "error": (
                f"Disallowed packages requested: {sorted(unknown)}. "
                "Only pre-installed packages may be used: "
                f"{sorted(ALLOWED_PACKAGES)}"
            ),
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        script = os.path.join(tmpdir, "model.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network=none",
                    "--memory=512m",
                    "--cpus=1",
                    "-v",
                    f"{tmpdir}:/sandbox:ro",
                    DOCKER_IMAGE,
                    "python",
                    "/sandbox/model.py",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {
                "stdout": None,
                "error": "Execution timed out after 120 seconds.",
            }
        except FileNotFoundError:
            return {
                "stdout": None,
                "error": (
                    "Docker is not available. "
                    "Ensure Docker is installed and running, "
                    f"and the image '{DOCKER_IMAGE}' has been built "
                    "(`just validator-build`)."
                ),
            }

        return {
            "stdout": proc.stdout or None,
            "error": proc.stderr if proc.returncode != 0 else None,
        }


async def run_and_validate_code_tool(
    ctx: RunContext[ValidatorDeps],
) -> dict[str, Any]:
    """Run the generated code in the Docker sandbox and return stdout/error."""
    if not ctx.deps.code:
        raise ValueError("Code is required.")
    return await execute_in_docker(ctx.deps.code, ctx.deps.dependencies)


class ValidatorAgent(Agent[ValidatorDeps, ValidatorOutput]):
    """Execute and validate generated models in an isolated Docker sandbox."""

    def __init__(self):
        """Initialise the ValidatorAgent with Docker-based sandbox execution."""
        super().__init__(
            model=openai_model,
            deps_type=ValidatorDeps,
            output_type=ValidatorOutput,
            instructions=validator_instructions,
            tools=[run_and_validate_code_tool],
            retries=3,
        )
