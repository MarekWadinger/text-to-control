from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from .base import get_model


@dataclass
class ExpertDeps:
    reformulation_code: str | None = None
    assumptions: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)


class ExpertInquiry(BaseModel):
    explanation: str
    clarification_questions: list[str]


class ProblemType(str, Enum):
    LP = "Linear Programming"
    ILP = "Integer Programming"
    MILP = "Mixed-Integer Programming"
    NLP = "Nonlinear Programming"
    SP = "Stochastic Programming"
    OTHER = "Other"


class ExpertOutput(BaseModel):
    reformulated_problem: str
    problem_type: ProblemType
    assumptions: list[str]


with open("src/instructions/expert.md") as f:
    expert_instructions = f.read()
with open("src/instructions/expert_pid.md") as f:
    pid_instructions = f.read()


class ExpertAgent:
    """Reformulate user optimization problems into structured form."""

    def __init__(self, api_key: str | None = None):
        self.agent: Agent[ExpertDeps, ExpertOutput | ExpertInquiry] = Agent(
            model=get_model(api_key),
            deps_type=ExpertDeps,
            output_type=[ExpertOutput, ExpertInquiry],
            instructions=expert_instructions,
            retries=3,
        )

        # --- PID tool ---
        @self.agent.tool
        async def pid_specialist(
            ctx: RunContext[ExpertDeps],
            problem_description: str,
        ) -> ExpertOutput:
            """
            Use this tool ONLY if the problem is about PID controller tuning.
            """
            reformulated_problem = (
                f"{pid_instructions}\n\nUser problem:\n{problem_description}"
            )
            return ExpertOutput(
                reformulated_problem=reformulated_problem,
                problem_type=ProblemType.NLP,
                assumptions=[],
            )

    # --- Run method ---
    async def run(self, user_input: str, deps: ExpertDeps | None = None):
        if deps is None:
            deps = ExpertDeps()

        pid_keywords = ["kp", "ki", "kd", "pid", "pi", "pd", "p", "controller"]
        if any(kw in user_input.lower() for kw in pid_keywords):
            # automaticky volá PID tool
            return await self.agent.tools["pid_specialist"](
                user_input, deps=deps
            )

        return await self.agent.run(user_input, deps=deps)
