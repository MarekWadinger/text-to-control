import anyio
from rich import print

from src.agents import (
    ExpertAgent,
    ExpertDeps,
    ExpertOutput,
    IntegratorAgent,
    IntegratorDeps,
    ValidatorAgent,
    ValidatorDeps,
)


async def main():
    """Run the Expert → Integrator → Validator pipeline asynchronously."""
    print("\n Starting Expert → Integrator → Validator pipeline...\n")

    # --- Expert step ---
    expert = ExpertAgent().agent
    optimization_prompt = open(
        "examples/allocation_problem.txt", "r", encoding="utf-8"
    ).read()

    while True:
        deps_expert = ExpertDeps()
        expert_result = await expert.run(optimization_prompt, deps=deps_expert)
        expert_output = expert_result.output

        if isinstance(expert_output, ExpertOutput):
            break
        else:
            print("\n Expert Agent requested clarification:\n")
            for question in expert_output.clarification_questions:
                print(" -", question)
            user_input = input(
                "\nProvide clarifications to the Expert Agent and press Enter to continue: "
            )
            optimization_prompt += f"\nClarifications: {user_input}\n"

    print("\n Expert Reformulation:\n")
    print(expert_output.reformulated_problem)
    print("\n Problem Type:", expert_output.problem_type)
    print("\n Assumptions:", expert_output.assumptions)

    # --- Integrator step ---
    integrator = IntegratorAgent().agent
    deps_integrator = IntegratorDeps(
        reformulated_text=expert_output.reformulated_problem,
        expert_assumptions=expert_output.assumptions,
    )

    expert_prompt = f"""
You are the Integrator Agent.
Your task is to write a runnable Pyomo model that **exactly** implements this problem:

{expert_output.reformulated_problem}

Assumptions:
{expert_output.assumptions}
"""

    print("\n Generating executable Pyomo model code...\n")
    integrator_result = await integrator.run(
        expert_prompt, deps=deps_integrator
    )
    output = integrator_result.output
    pyomo_code = (
        output.code.strip() if hasattr(output, "code") else output.strip()
    )

    print("Generated Pyomo Code Preview:\n")
    print(pyomo_code[:800], "...\n")

    with open("generated_code.py", "w", encoding="utf-8") as f:
        f.write(pyomo_code)
    print(" Model code saved to generated_code.py \n")

    # --- Validator step ---
    validator = ValidatorAgent().agent
    deps_validator = ValidatorDeps(code=pyomo_code)

    print("\n Validating the generated Pyomo model...\n")
    validator_result = await validator.run("", deps=deps_validator)
    validation_output = validator_result.output

    print("\n Validation Results:\n")
    print("Success:", validation_output.success)
    print("Error:", validation_output.error)
    print("\n--- Solver Output ---\n")
    print(validation_output.stdout)
    print("----------------------")
    print("Objective Name:", validation_output.objective_name)
    print("Objective Value:", validation_output.objective_value)
    print("\n Pipeline completed successfully!\n")


if __name__ == "__main__":
    anyio.run(main)
