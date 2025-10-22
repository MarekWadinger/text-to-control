import contextlib
import io
import os
import runpy
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config import Settings

# Model setup - API key and model initialization

settings = Settings()
provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel("gemini-flash-lite-latest", provider=provider)


#  Model setup - safe code execution


def safe_execute_python_code(code: str) -> dict[str, Any]:
    """Execute Python code safely and capture output and errors. Return stdout and values of a Pyomo model objective if present."""
    output_capture = io.StringIO()
    tmp_dir = tempfile.mkdtemp(prefix="code_sandbox_")
    script_path = os.path.join(tmp_dir, "model.py")

    # write code to temporary file - this helps with runpy

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    result: dict[str, Any] = {}

    try:
        with contextlib.redirect_stdout(output_capture):
            ns = runpy.run_path(script_path)

        result["stdout"] = output_capture.getvalue()
        result["error"] = None

        model = ns.get("model", None)
        if model is not None:
            try:
                from pyomo.core import Objective

                objs = [
                    c for c in model.component_objects(Objective, active=True)
                ]
                if objs:
                    obj = objs[0]
                    result["objective_name"] = obj.name
                    try:
                        result["objective_value"] = obj()
                    except Exception:
                        result["objective_value"] = "Unknown (not solved)"
            except Exception as e:
                result["objective_error"] = str(e)

    except Exception as e:
        result["stdout"] = output_capture.getvalue()
        result["error"] = str(e)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result


# deps dataclasses for agents


@dataclass
class ExpertDeps:
    """Store inputs and transient state used by the ExpertAgent.

    Attributes:
        reformulation_code: Code or text produced by the Expert (if any).
        assumptions: Assumptions recorded by the Expert.
        history: Clarification questions asked so far.
    """

    reformulation_code: str | None = None
    assumptions: list[str] | None = field(default_factory=list)
    history: list[str] | None = field(default_factory=list)


@dataclass
class IntegratorDeps:
    """Hold data passed to the IntegratorAgent for building runnable code.

    Attributes:
        reformulated_text: Reformulated problem text from the Expert.
        expert_assumptions: Assumptions provided by the Expert.
        generated_code: Pyomo code produced by the Integrator.
    """

    reformulated_text: str | None = None
    expert_assumptions: list[str] | None = field(default_factory=list)
    generated_code: str | None = None


@dataclass
class ValidatorDeps:
    """Contain the code and artifacts used by the ValidatorAgent during execution.

    Attributes:
        code: The Pyomo model code to validate.
        results: Solver/validation results, if available.
        logs: Captured stdout/stderr from execution.
    """

    code: str | None = None
    results: dict[str, Any] | None = None
    logs: str | None = None


# output schemas for agents


class ExpertInquiry(BaseModel):
    """Schema for the ExpertAgent inquiry: questions to clarify problem."""

    explanation: str
    clarification_questions: list[str]


class ProblemType(str, Enum):
    """Enumeration of problem types."""

    LP = "Linear Programming"
    ILP = "Integer Programming"
    MILP = "Mixed-Integer Programming"
    NLP = "Nonlinear Programming"
    SP = "Stochastic Programming"
    OTHER = "Other"


class ExpertOutput(BaseModel):
    """Schema for the ExpertAgent output: reformulated problem text and assumptions."""

    reformulated_problem: str
    problem_type: ProblemType
    assumptions: list[str]


class IntegratorOutput(BaseModel):
    """Schema for the IntegratorAgent output: generated Pyomo implementation code."""

    code: str


class ValidatorOutput(BaseModel):
    """Schema for the ValidatorAgent output: validation status, logs, and optional objective info."""

    success: bool
    stdout: str | None = None
    error: str | None = None
    objective_name: str | None = None
    objective_value: Any | None = None


# instructions
with open("src/instructions/expert.md") as f:
    expert_instructions = f.read()

#  Expert Agent


class ExpertAgent:
    """Reformulate user optimization problems into polished tasks while asking clarifying questions."""

    def __init__(self):
        """Create the Expert agent configured to analyze problems and emit reformulations or clarification questions."""
        self.agent = Agent(
            model,
            deps_type=ExpertDeps,
            output_type=[ExpertOutput, ExpertInquiry],
            retries=3,
            instructions=expert_instructions,
        )


#  Integrator Agent


class IntegratorAgent:
    """Generate runnable Pyomo scripts from the ExpertAgent's reformulated problem."""

    def __init__(self):
        """Create the Integrator agent configured to turn reformulations into runnable Pyomo code."""
        self.agent = Agent(
            model,
            deps_type=IntegratorDeps,
            output_type=IntegratorOutput,
            retries=3,
            system_prompt=(
                "You are the **Integrator Agent**, a senior optimization engineer specialized in Pyomo modeling.\n\n"
                "Your task is to take the reformulated optimization problem from the Expert Agent "
                "(provided in `ctx.deps.reformulated_text`) and implement it as a **complete runnable Pyomo script**.\n\n"
                "### Implementation rules:\n"
                "- Use only Pyomo (import pyomo.environ as pyo).\n"
                "- Always create `model = pyo.ConcreteModel()`.\n"
                "- Define all parameters, variables, objective, and constraints exactly as in the problem.\n"
                "- Do **not** create or assume any missing data.\n"
                "- If any data, parameters, or sets required for the model are missing (e.g., demands, costs, revenues, etc.),\n"
                "  **do not invent placeholder/sample values**. Instead, output a clear message like:\n"
                "  `Missing data detected: please provide [list of missing elements] before code generation.`\n"
                "- In such a case, stop immediately and do not generate any code.\n"
                "- After defining the model (if all data is available), add this solving section exactly:\n"
                "  solver = pyo.SolverFactory('glpk')\n"
                "  if not solver.available():\n"
                "      solver = pyo.SolverFactory('cbc')\n"
                "  results = solver.solve(model, tee=True)\n"
                "  print('Solver Status:', results.solver.status)\n"
                "  print('Termination Condition:', results.solver.termination_condition)\n"
                "  for v in model.component_objects(pyo.Var, active=True):\n"
                "      for index in v:\n"
                "          print(f'{v.name}[{index}] =', pyo.value(v[index]))\n"
                "  print('Objective Value:', pyo.value(model.obj))\n\n"
                "- Do not rename variables or omit the solve step.\n"
                "- Output only the runnable Python code — no comments or markdown.\n\n"
                "### Output behavior:\n"
                "- If all required data is present → produce runnable Pyomo code.\n"
                "- If any data is missing → produce a clear textual message asking for the missing data, not code.\n\n"
                "### Reformulated problem text to implement:\n"
                "{ctx.deps.reformulated_text}\n\n"
                "### Expert assumptions:\n"
                "{ctx.deps.expert_assumptions}\n\n"
                "Your output should implement exactly this model, without adding or changing anything."
            ),
        )


#  Validator Agent


class ValidatorAgent:
    """Run and validate Pyomo models in a sandbox, reporting stdout, solver status, and objective value.

    Attributes:
        agent: Configured Agent instance responsible for executing and validating the model.
    """

    def __init__(self):
        """Create the Validator agent configured to execute code safely and capture results."""
        self.agent = Agent(
            model,
            deps_type=ValidatorDeps,
            output_type=ValidatorOutput,
            retries=3,
            system_prompt=(
                "You are the **Validator Agent**. "
                "Execute the provided Pyomo code safely in a sandbox. "
                "Capture stdout, solver status, and objective value if available. "
                "Report success or failure clearly."
            ),
        )

        @self.agent.tool()
        def run_and_validate_code(
            ctx: RunContext[ValidatorDeps],
        ) -> dict[str, Any]:
            """Run the provided Pyomo code and validate the results."""
            return safe_execute_python_code(ctx.deps.code or "")


# wrapper for all agents for easy access


class AgentsSuite:
    """A suite encapsulating the Expert, Integrator, and Validator agents."""

    def __init__(self):
        """Initialize the AgentsSuite with pre-configured agent instances.

        Creates these attributes:
        - expert: ExpertAgent.agent
        - integrator: IntegratorAgent.agent
        - validator: ValidatorAgent.agent
        """
        self.expert = ExpertAgent().agent
        self.integrator = IntegratorAgent().agent
        self.validator = ValidatorAgent().agent
