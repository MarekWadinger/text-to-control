import asyncio
from collections.abc import Callable

import logfire
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_evals import Dataset

from config import Settings
from src.agents.integrator import IntegratorDeps
from src.agents.validator import ValidatorDeps
from src.pipeline import expert, integrator, pipeline, validator

load_dotenv()

settings = Settings()
# Configure Logfire for logging and tracing
logfire.configure(
    token=settings.logfire_token,
    send_to_logfire="if-token-present",
    distributed_tracing=False,
    service_name="evals",
    environment=settings.environment,
)

logfire.instrument_pydantic_ai()


async def expert_task(inputs: str):
    """Task function to be evaluated: Runs the expert agent.

    Receives: inputs (str)
    Returns: ExpertOutput with success, stdout, error, and clarification_questions.
    """
    with logfire.span("expert_task"):
        expert_result = await expert.run(inputs)
    return expert_result.output


async def integrator_task(inputs: dict):
    """Task function to be evaluated: Runs the integrator agent.

    Receives: inputs (dict)
    Returns: IntegratorOutput with success, stdout, error, and code.
    """
    with logfire.span("integrator_task"):
        deps = IntegratorDeps.model_validate(inputs)
        integrator_result = await integrator.run(deps=deps)
    return integrator_result.output


async def validator_task(inputs: str):
    """Task function to be evaluated: Runs the validator agent.

    Receives: inputs (str)
    Returns: ValidatorOutput with success, stdout, error, objective_name, and objective_value.
    """
    with logfire.span("validator_task"):
        deps = ValidatorDeps.model_validate(inputs)
        validator_result = await validator.run(deps=deps)
    return validator_result.output


async def pipeline_task(prompt: str):
    """Task function to be evaluated: Validates the optimization model.

    Receives: prompt (str)
    Returns: ValidatorOutput with success, stdout, error, objective_name, and objective_value.
    """
    with logfire.span("pipeline_task"):
        validator_run = await pipeline(prompt, clarification_mode="ignore")

    return validator_run


class Suite(BaseModel):
    prefix: str
    task: Callable


SUITES: list[Suite] = [
    Suite(prefix="expert", task=expert_task),
    Suite(prefix="integrator", task=integrator_task),
    Suite(prefix="validator", task=validator_task),
    Suite(prefix="pipeline", task=pipeline_task),
]


async def main():
    dataset_bundle = Dataset.from_file("datasets/basics.yaml")

    # 1) Split cases into suite datasets
    suite_datasets: dict[str, Dataset] = {
        suite.prefix: Dataset(
            cases=[], evaluators=list(dataset_bundle.evaluators)
        )
        for suite in SUITES
    }

    for case in dataset_bundle.cases:
        matched = False
        for suite in SUITES:
            if str(case.name).startswith(suite.prefix + "_"):
                if case.name:
                    case.name = case.name.removeprefix(suite.prefix + "_")
                suite_datasets[suite.prefix].cases.append(case)
                matched = True
                break
        if not matched:
            # optionally record unmatched now, or just detect later
            logfire.warning(
                f"Case {case.name} is not a valid case name. "
                f"Prefix should be one of {', '.join(suite.prefix for suite in SUITES)}."
            )

    # 2) Run suites only if they have cases
    for suite in SUITES:
        ds = suite_datasets[suite.prefix]
        if not ds.cases:
            continue
        report = await ds.evaluate(suite.task)
        logfire.info(f"{suite.prefix.capitalize()} Report:")
        report.print()


if __name__ == "__main__":
    asyncio.run(main())
