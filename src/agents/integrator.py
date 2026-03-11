import os
import subprocess
import tempfile

import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.format_prompt import format_as_xml
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import (
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)

from .base import openai_provider
from .expert import ExpertOutput

# Packages available inside the Docker sandbox.
# Normalise dependency strings (strip version specifiers and extras)
# before checking membership.
ALLOWED_PACKAGES = {
    "pyomo",
    "cvxpy",
    "casadi",
    "numpy",
    "scipy",
    "sympy",
    "pandas",
    "matplotlib",
    "control",
    "python-control",
    "slycot",
}

# Codex model
codex_model_settings = OpenAIResponsesModelSettings(
    # TODO: Figure out how to use Code Interpreter with pydantic-ai
    # openai_builtin_tools=[
    #     {
    #         "type": "code_interpreter",
    #         "container": {"type": "auto", "memory_limit": "4g"},
    #     }
    # ]
)

codex_model = FallbackModel(
    *[
        OpenAIResponsesModel(
            model, provider=openai_provider, settings=codex_model_settings
        )
        for model in ["gpt-5.2-codex", "gpt-5.1-codex", "gpt-5-codex"]
    ],
)


class IntegratorDeps(ExpertOutput): ...


class IntegratorOutput(BaseModel):
    dependencies: list[str] = Field(
        default_factory=list,
        description="External python package dependencies to import. Allowed packages are: "
        + ", ".join(ALLOWED_PACKAGES)
        + ".",
    )
    code: str = Field(description="The code to run.")


class CodeFailure(BaseModel):
    """An unrecoverable failure. Only use this when you can't generate valid code."""

    reason: str


with open("src/instructions/integrator.md", encoding="utf-8") as f:
    integrator_instructions = f.read()


def ruff_check(code: str) -> str:
    """Run Ruff on generated code and auto-fix issues."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(code.encode("utf-8"))
        tmp.flush()
        path = tmp.name

    try:
        process = subprocess.run(
            ["uvx", "ruff", "check", "--fix", path],
            capture_output=True,
            text=True,
        )

        output = (process.stdout or "").strip()

        if "All checks passed!" in output or process.returncode == 0:
            logfire.info("\n[Ruff] Code passed or auto-fixed successfully.\n")
            with open(path, encoding="utf-8") as f:
                return f.read()

        raise ModelRetry(
            f"Ruff lint found critical issues that could not be auto-fixed.\n"
            f"Regenerate the code so that it passes Ruff lint cleanly.\n\n"
            f"Ruff output:\n{output}"
        )

    finally:
        if os.path.exists(path):
            os.remove(path)


def code_no_msglev_check(code: str) -> str:
    """Run check to verify that the code does not contain the msglev option."""
    if "--msglev" in code:
        raise ModelRetry(
            "The code contains the msglev option, which is prohibited."
        )
    return code


def check_code(code: str) -> IntegratorOutput:
    """Check bundle for the code validation."""
    code = ruff_check(code)
    code = code_no_msglev_check(code)
    return IntegratorOutput(code=code)


async def instructions(ctx: RunContext[IntegratorDeps]) -> str:
    return (
        integrator_instructions
        + "\n"
        + format_as_xml(ctx.deps, root_tag="problem")
    )


class IntegratorAgent(Agent[IntegratorDeps, IntegratorOutput | CodeFailure]):
    """Generate runnable code from the ExpertAgent's reformulated problem."""

    def __init__(self):
        """Create the Integrator configured to generate and validate code."""
        super().__init__(
            model=codex_model,
            deps_type=IntegratorDeps,
            output_type=[check_code, CodeFailure],
            instructions=instructions,
            retries=3,
        )
