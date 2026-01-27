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


async def main(prompt: str):
    """Run Expert → Integrator → Validator pipeline and return summary."""
    messages = []

    # --- Expert Step ---
    expert = ExpertAgent().agent
    optimization_prompt = prompt
    while True:
        deps_expert = ExpertDeps()
        expert_result = await expert.run(optimization_prompt, deps=deps_expert)
        expert_output = expert_result.output

        if isinstance(expert_output, ExpertOutput):
            break
        else:
            messages.append(" Expert requires clarification:\n")
            for q in expert_output.clarification_questions:
                messages.append(f" - {q}")
            # pipeline zastaví, aby frontend vedel ukázať klarifikáciu
            raise RuntimeError(
                "\n".join(expert_output.clarification_questions)
            )

    if not isinstance(expert_output, ExpertOutput):
        raise RuntimeError("Expert agent response was not finalized.")

    # --- Integrator Step ---
    integrator = IntegratorAgent().agent
    deps_integrator = IntegratorDeps(
        reformulated_problem=expert_output.reformulated_problem,
        problem_type=expert_output.problem_type,
        assumptions=expert_output.assumptions,
    )
    integrator_prompt = f"""
You are the Integrator Agent.
Write a runnable Pyomo model for:

{expert_output.reformulated_problem}

Assumptions:
{expert_output.assumptions}
"""
    integrator_result = await integrator.run(
        integrator_prompt, deps=deps_integrator
    )
    output = integrator_result.output
    if isinstance(output, IntegratorOutput):
        pyomo_code = output.code.strip()
    else:
        pyomo_code = str(output).strip()

    with open("generated_code.py", "w", encoding="utf-8") as f:
        f.write(pyomo_code)

    # --- Validator Step ---
    validator = ValidatorAgent().agent
    deps_validator = ValidatorDeps(code=pyomo_code)
    validator_result = await validator.run("", deps=deps_validator)
    validation_output = validator_result.output

    # --- Summary ---
    messages.append(f" Success: {validation_output.success}")
    if getattr(validation_output, "objective_name", None):
        messages.append(f"Objective Name: {validation_output.objective_name}")
    if getattr(validation_output, "objective_value", None) is not None:
        messages.append(
            f"Objective Value: {validation_output.objective_value}"
        )
    if getattr(validation_output, "stdout", None):
        messages.append(f"Solver output:\n{validation_output.stdout}")
    return "\n".join(messages)
