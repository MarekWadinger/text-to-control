"""Run the Expert → Integrator → Validator pipeline."""

import anyio
import logfire

from config import Settings
from src.agents import (
    ExpertAgent,
    ExpertDeps,
    ExpertOutput,
    IntegratorAgent,
    IntegratorDeps,
    IntegratorOutput,
    ValidatorAgent,
    ValidatorDeps,
)

# configure logfire
logfire.configure(token=Settings().logfire_token)
logfire.instrument_pydantic_ai()


async def main():
    """Run the Expert → Integrator → Validator pipeline."""
    with logfire.span("run"):
        logfire.info(
            "\n Starting Expert → Integrator → Validator pipeline...\n"
        )

        # --- Expert step ---
        with logfire.span("expert"):
            expert = ExpertAgent().agent
            optimization_prompt = open(
                "examples/pid_1.txt", encoding="utf-8"
            ).read()

            while True:
                deps_expert = ExpertDeps()
                expert_result = await expert.run(
                    optimization_prompt, deps=deps_expert
                )
                expert_output = expert_result.output

                if isinstance(expert_output, ExpertOutput):
                    break
                else:
                    logfire.info("\n Expert Agent requested clarification:\n")
                    for question in expert_output.clarification_questions:
                        logfire.info(f" - {question}")

                    user_input = input(
                        (
                            "\nProvide clarifications to the Expert Agent ",
                            "and press Enter to continue: ",
                        )
                    )
                    optimization_prompt += f"\nClarifications: {user_input}\n"

        if not isinstance(expert_output, ExpertOutput):
            raise RuntimeError("Expert agent response was not finalized.")

        # --- Integrator step ---
        with logfire.span("integrator"):
            integrator = IntegratorAgent().agent
            deps_integrator = IntegratorDeps(
                reformulated_problem=expert_output.reformulated_problem,
                problem_type=expert_output.problem_type,
                assumptions=expert_output.assumptions,
            )

            expert_prompt = f"""
        You are the Integrator Agent.
        Your task is to write a runnable Pyomo model that **exactly**
        implements this problem:

        {expert_output.reformulated_problem}

        Assumptions:
        {expert_output.assumptions}
        """

            logfire.info("\n Generating executable model code...\n")
            integrator_result = await integrator.run(
                expert_prompt, deps=deps_integrator
            )
            output = integrator_result.output
            if isinstance(output, IntegratorOutput):
                pyomo_code = output.code.strip()
            else:
                pyomo_code = str(output).strip()

            logfire.info("Generated Code Preview:\n")
            logfire.info(f"{pyomo_code[:800]}...\n")

            with open("generated_code.py", "w", encoding="utf-8") as f:
                f.write(pyomo_code)
            logfire.info(" Model code saved to generated_code.py \n")

        # --- Validator step ---
        with logfire.span("validator"):
            validator = ValidatorAgent().agent
            deps_validator = ValidatorDeps(code=pyomo_code)

            logfire.info("\n Validating the generated Pyomo model...\n")
            validator_result = await validator.run("", deps=deps_validator)
            validation_output = validator_result.output

            logfire.info("\n Validation Results:\n")
            logfire.info(f"Success: {validation_output.success}")
            if validation_output.error:
                logfire.info(f"Error: {validation_output.error}")
            logfire.info("\n--- Solver Output ---\n")
            if validation_output.stdout is not None:
                logfire.info(validation_output.stdout)
            logfire.info("----------------------")
            if validation_output.objective_name:
                logfire.info(
                    f"Objective Name: {validation_output.objective_name}"
                )
            if validation_output.objective_value is not None:
                logfire.info(
                    f"Objective Value: {validation_output.objective_value}"
                )
            logfire.info("\n Pipeline completed successfully!\n")


if __name__ == "__main__":
    anyio.run(main)
