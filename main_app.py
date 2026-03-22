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

logfire.configure(token=Settings().logfire_token)
logfire.instrument_pydantic_ai()

MAX_RETRIES = 3


async def main(prompt: str):
    """Run Expert → Integrator → Validator pipeline with retry loop."""
    messages = []

    # --- Expert Step ---
    expert = ExpertAgent().agent
    while True:
        deps_expert = ExpertDeps()
        expert_result = await expert.run(prompt, deps=deps_expert)
        expert_output = expert_result.output

        if isinstance(expert_output, ExpertOutput):
            break
        else:
            raise RuntimeError(
                "\n".join(expert_output.clarification_questions)
            )

    # --- Integrator + Validator retry loop ---
    last_error = None
    for attempt in range(MAX_RETRIES):
        integrator_prompt = f"""
You are the Integrator Agent.
Write a runnable Python model for:

{expert_output.reformulated_problem}

Assumptions:
{expert_output.assumptions}
"""
        if last_error:
            integrator_prompt += f"""

IMPORTANT: Previous attempt failed with this error:
{last_error}

Fix the code so this error does not occur.
"""

        # --- Integrator Step ---
        integrator = IntegratorAgent().agent
        deps_integrator = IntegratorDeps(
            reformulated_problem=expert_output.reformulated_problem,
            problem_type=expert_output.problem_type,
            assumptions=expert_output.assumptions,
        )
        integrator_result = await integrator.run(
            integrator_prompt, deps=deps_integrator
        )
        output = integrator_result.output
        pyomo_code = (
            output.code.strip()
            if isinstance(output, IntegratorOutput)
            else str(output).strip()
        )

        with open("generated_code.py", "w", encoding="utf-8") as f:
            f.write(pyomo_code)

        # --- Validator Step ---
        validator = ValidatorAgent().agent
        deps_validator = ValidatorDeps(code=pyomo_code)
        validator_result = await validator.run("", deps=deps_validator)
        validation_output = validator_result.output

        if validation_output.success:
            # Pokiaľ Validator vracia stdout ako dict, vyber len relevantné polia
            result = validation_output.stdout or {}

            # Pre NLP/PID problémy:
            if result.get("problem_type") in ("NLP", "PID", "NLP_PID"):
                controller = result.get("controller", {})
                performance = result.get("performance", {})
                messages.append(f"Kp: {controller.get('Kp')}")
                messages.append(f"Ki: {controller.get('Ki')}")
                messages.append(f"Kd: {controller.get('Kd')}")
                messages.append(
                    f"Overshoot [%]: {performance.get('overshoot_percent')}"
                )
                messages.append(
                    f"Settling Time [s]: {performance.get('settling_time_seconds')}"
                )
                messages.append(f"ISE: {performance.get('ISE')}")

            # Pre LP/MILP problémy:
            elif result.get("problem_type") in ("LP", "MILP"):
                messages.append(
                    f"Objective Value: {result.get('objective_value')}"
                )
                for var_name, value in result.get("variables", {}).items():
                    messages.append(f"{var_name} = {value}")

            return "\n".join(messages)

        # --- Pokračovanie pre prípad chyby ---
        last_error = (
            validation_output.error
            or validation_output.stdout
            or "Unknown error"
        )
        messages.append(f"Attempt {attempt + 1} failed: {last_error}")

    messages.append(f"Failed after {MAX_RETRIES} attempts.")
    messages.append(f"Last error: {last_error}")
    return "\n".join(messages)
