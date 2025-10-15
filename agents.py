import contextlib
import io
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config import Settings

# Model setup
settings = Settings()
provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel("gemini-flash-lite-latest", provider=provider)


#   ------------------------------------------------------------


def safe_execute_python_code(code: str) -> dict[str, Any]:
    """Executes Python code safely and captures output and errors."""
    local_vars = {}
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {}, local_vars)
        return {"stdout": output_buffer.getvalue(), "locals": local_vars}
    except Exception as e:
        return {"error": str(e), "stdout": output_buffer.getvalue()}


# -------------------------------------------------------------


@dataclass
class ExpertDeps:
    generated_code: str | None = None
    results: dict[str, Any] | None = None
    history: list[str] = field(default_factory=list)


@dataclass
class IntegratorDeps:
    expert_code: str | None = None
    expert_results: dict[str, Any] | None = None


# -------------------------------------------------------------


class CodeOutput(BaseModel):
    explanation: str
    code: str


class FeedbackOutput(BaseModel):
    correctness: str
    efficiency: str
    best_practices: str
    improvement_suggestions: str


# -------------------------------------------------------------
class MyAgent:
    def __init__(self, role: str):
        self.role = role.lower()

        if self.role == "expert":
            self.agent = Agent(
                model,
                deps_type=ExpertDeps,
                output_type=CodeOutput,
                retries=3,
                system_prompt=(
                    "You are the **Expert Agent**, a professional in optimization modeling. "
                    "Your task is to read the user's natural language description of an optimization problem "
                    "and generate a working Pyomo model (complete Python code). "
                    "Do not call any functions or tools. Just produce code directly. "
                    "Always use `import pyomo.environ as pyo` at the start. "
                    "Define all sets explicitly with `pyo.Set()`, "
                    "and include `SolverFactory('glpk')` or `SolverFactory('ipopt')`."
                ),
            )

        elif self.role == "integrator":
            self.agent = Agent(
                model,
                deps_type=IntegratorDeps,
                output_type=FeedbackOutput,
                retries=3,
                system_prompt=(
                    "You are the **Integrator Agent**, an expert code reviewer. "
                    "Analyze the Pyomo code provided by the Expert Agent. "
                    "Check correctness, structure, and optimization best practices. "
                    "Do not call any tools; return only text feedback with four parts: "
                    "`correctness`, `efficiency`, `best_practices`, and `improvement_suggestions`."
                ),
            )

        else:
            raise ValueError(
                "Invalid role name. Use 'Expert' or 'Integrator'."
            )

    # -----------------------------------------------------

    async def solve_task(self, prompt: str, deps=None):
        print(f"\n[{self.role.title()}] is reasoning...\n")

        try:
            result = await self.agent.run(
                prompt
                + "\n (Do not call any tools or functions; just return structured text output.)",
                deps=deps,
            )
            return result

        except Exception as e:
            print(f" Model error handled: {e}")
            print(" Retrying with simplified text-only reasoning...\n")
            return await self.agent.run(
                prompt
                + "\n Return the result as plain text only, no functions or JSON.",
                deps=deps,
            )
