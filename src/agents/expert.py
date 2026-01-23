from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel
from pydantic_ai import Agent

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
