import asyncio

import logfire
from pydantic_evals import Dataset

from config import Settings
from src.pipeline import pipeline

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


# Create a dataset with test cases
dataset = Dataset.from_file("datasets/control.yaml")


async def validator_task(case_inputs: str):
    """Task function to be evaluated: Validates the optimization model.

    Receives: case_inputs (str)
    Returns: ValidatorOutput with success, stdout, error, objective_name, and objective_value.
    """
    validator_run = await pipeline(case_inputs, clarification_mode="ignore")

    return validator_run.output


async def main():
    # Run the evaluation
    report = await dataset.evaluate(validator_task)

    # Print the results
    report.print()


if __name__ == "__main__":
    asyncio.run(main())
