from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .base import openai_model


class ClarificationQuestion(BaseModel):
    """Question for the user to clarify the problem."""

    question: str = Field(
        description="A clear question for the user to help clarify the problem, using language that matches the user's likely expertise. Avoid any technical terms or jargon unless the user obviously has advanced knowledge.",
    )
    choices: list[str] = Field(
        default_factory=list,
        description="A list of maximum three **one-word choices**, sorted by assumed relevance and highly relevant to the optimal decision making, to present to the user if possible to choose from for clarification.",
        max_length=3,
    )


class ExpertInquiry(BaseModel):
    """Inquiry for the user to clarify the problem."""

    explanation: str = Field(
        description="Inquiry with why these questions are asked to the user."
    )
    clarification_questions: list[ClarificationQuestion]


class ProblemType(str, Enum):
    LP = "Linear Programming"
    ILP = "Integer Programming"
    MILP = "Mixed-Integer Programming"
    NLP = "Nonlinear Programming"
    SP = "Stochastic Programming"
    OTHER = "Other"


class ExpertOutput(BaseModel):
    reformulated_problem: str = Field(
        description="The reformulated problem in LaTeX format."
    )
    problem_type: ProblemType
    assumptions: list[str] = Field(
        description="A list of assumptions explicitly made only because the user could not provide details. Never assume anything that you have not directly queried and confirmed with the user."
    )


with open("src/instructions/expert.md") as f:
    expert_instructions = f.read()


def pid_cookbook(ctx: RunContext[str]) -> str:
    """Use this cookbook for PID tuning problems."""
    return open("src/instructions/expert_cookbooks/pid.md").read()


def allocation_cookbook(ctx: RunContext[str]) -> str:
    """Use this cookbook for resource allocation problems."""
    return open("src/instructions/expert_cookbooks/allocation.md").read()


class ExpertAgent(Agent[str, ExpertOutput | ExpertInquiry]):
    """Reformulate user optimization problems into structured form."""

    def __init__(
        self,
        model: str = openai_model,
        instructions: str = expert_instructions,
    ):
        super().__init__(
            model=model,
            output_type=[ExpertOutput, ExpertInquiry],
            instructions=instructions,
            tools=[pid_cookbook, allocation_cookbook],
        )
