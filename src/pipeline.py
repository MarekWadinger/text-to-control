"""Run the Expert → Integrator → Validator pipeline."""

from typing import Literal

import logfire
from pydantic_ai import UsageLimits
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import RunUsage
from rich.prompt import Prompt

from config import Settings
from src.agents import (
    ExpertAgent,
    ExpertOutput,
    IntegratorAgent,
    ValidatorAgent,
)
from src.agents.expert import ClarificationQuestion, ExpertInquiry
from src.agents.integrator import CodeFailure
from src.agents.validator import ValidatorOutput

logfire.configure(token=Settings().logfire_token)
logfire.instrument_pydantic_ai()

expert = ExpertAgent()
integrator = IntegratorAgent()
validator = ValidatorAgent()

ClarificationMode = Literal["prompt", "raise", "ignore"]


class ClarificationNeeded(RuntimeError):
    """Signal that the user must clarify their request."""

    def __init__(self, inquiry: ExpertInquiry) -> None:
        """Initialize with a formatted clarification message."""
        self.inquiry = inquiry
        super().__init__(inquiry)


def _prompt_for_clarification(question: ClarificationQuestion) -> str:
    """Prompt for clarification in a CLI environment."""
    return Prompt.ask(
        question.question,
        choices=question.choices if question.choices else None,
        show_default=True,
        show_choices=True,
    )


async def pipeline(
    prompt: str,
    clarification_mode: ClarificationMode = "raise",
) -> ValidatorOutput:
    """Run Expert → Integrator → Validator pipeline and return validator output.

    Args:
        prompt: User's initial problem description.
        clarification_mode: Strategy for handling clarification questions.
            - "prompt": ask questions interactively in the CLI using `rich.Prompt`.
            - "raise": raise `ClarificationNeeded` when clarifications are requested.
            - "ignore": skip clarification questions and ask the expert to
              proceed with reasonable assumptions instead of querying the user.
    """
    expert_history: list[ModelMessage] | None = None
    usage: RunUsage = RunUsage()
    usage_limits = UsageLimits(request_limit=15)

    if clarification_mode == "ignore":
        prompt += "\n" + (
            "CRITICAL: Clarification questions are disabled. Proceed with the problem using reasonable assumptions, and list all assumptions explicitly."
        )

    # --- Expert Step ---
    # Convert to streaming response
    with logfire.span("expert"):
        # Inquiry loop
        while True:
            expert_result = await expert.run(
                prompt,
                message_history=expert_history,
                output_type=ExpertOutput
                if clarification_mode
                == "ignore"  # Override output type for ignore mode
                else None,
                usage=usage,
                usage_limits=UsageLimits(request_limit=5),
            )
            expert_output = expert_result.output

            if isinstance(expert_output, ExpertOutput):
                break
            else:
                if clarification_mode == "raise":
                    raise ClarificationNeeded(expert_output)

                elif clarification_mode == "prompt":
                    answers = [
                        _prompt_for_clarification(question)
                        for question in expert_output.clarification_questions
                    ]
                    expert_history = expert_result.all_messages(
                        output_tool_return_content=(
                            f"Clarifications answers: \n{'\n'.join(answers)}"
                        )
                    )
                    continue

    # --- Integrator Step ---
    with logfire.span("integrator"):
        integrator_result = await integrator.run(
            deps=expert_output,
            usage=usage,
            usage_limits=usage_limits,
        )
        code = integrator_result.output
        if isinstance(code, CodeFailure):
            raise RuntimeError(f"IntegratorAgent failed: {code.reason}")

        with open("generated_code.py", "w", encoding="utf-8") as f:
            f.write(code.code)

    # --- Validator Step ---
    with logfire.span("validator"):
        validator_result = await validator.run(
            deps=code,
            usage=usage,
            usage_limits=usage_limits,
        )
        validation_output = validator_result.output

        return validation_output
