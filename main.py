import anyio

from agents import (
    AgentsSuite,
    ExpertDeps,
    ExpertOutput,
    IntegratorDeps,
    ValidatorDeps,
)


async def main():
    """Run the Expert → Integrator → Validator pipeline asynchronously.

    Start the agents suite, send the optimization prompt to the Expert agent,
    and coordinate subsequent Integrator and Validator steps.
    """
    print("\n Starting Expert → Integrator → Validator pipeline...\n")

    suite = AgentsSuite()

    # expert Step

    optimization_prompt = """
A farmer is growing two types of vegetables: Tomatoes and Cucumbers.

Available resources:
- Land: 1000 m²
- Water: 3000 liters

Material usage per crop:
- Tomatoes: 5 m² + 30 liters of water per plant
- Cucumbers: 3 m² + 20 liters of water per plant

Profit per plant:
- Tomatoes: 4 €
- Cucumbers: 3 €

Goal:
Help me maximize my profit by determining how many plants of each vegetable I should grow, considering the land and water constraints.
"""
    # TODO: Implement max reties or clarification loop
    while True:
        deps_expert = ExpertDeps()
        expert_result = await suite.expert.run(
            optimization_prompt, deps=deps_expert
        )
        expert_output = expert_result.output
        if isinstance(expert_output, ExpertOutput):
            break
        else:
            print(
                " Expert Agent requested clarification. Please address the following questions:\n"
            )
            for question in expert_output.clarification_questions:
                print(" -", question)
            user_input = input(
                "\n Provide clarifications to the Expert Agent and press Enter to continue..."
            )
            optimization_prompt += f"\nClarifications: {user_input}\n"

    print(" [Expert Reformulation]:\n")
    print(expert_output.reformulated_problem)
    print(" [Problem Type]:\n")
    print(expert_output.problem_type)
    print("\n [Assumptions]:", expert_output.assumptions)

    # integrator Step
    deps_integrator = IntegratorDeps(
        reformulated_text=expert_output.reformulated_problem,
        expert_assumptions=expert_output.assumptions,
    )
    # Create the prompt for the Integrator Agent - halucinations fix

    integrator_prompt = f"""
You are the Integrator Agent.
Your task is to write a runnable Pyomo model that **exactly** implements this problem:

{expert_output.reformulated_problem}

Assumptions:
{expert_output.assumptions}

Rules:
- Use only Pyomo (import pyomo.environ as pyo).
- Do NOT import numpy, pandas, or any other package.
- Define model = pyo.ConcreteModel().
- Implement sets, parameters, variables, objective, and constraints exactly as written.
- Do not invent any new data, sets, or structure.
- Use GLPK solver; fallback to CBC if GLPK is unavailable.
- After solving, print solver status, variable values, and objective value.
- Output only pure Python code (no markdown, explanations, or comments).
- The final script will be saved as 'generated_code.py'.
"""

    print("\n Generating executable Pyomo model code...\n")
    integrator_result = await suite.integrator.run(
        integrator_prompt, deps=deps_integrator
    )
    integrator_output = integrator_result.output

    pyomo_code = integrator_output.code.strip()
    print(" [Generated Pyomo Code Preview]:\n")
    print(pyomo_code[:800], "...\n")

    with open("generated_code.py", "w", encoding="utf-8") as f:
        f.write(pyomo_code)
    print(" Model code saved to generated_code.py\n")

    # Validation Step

    print(" Validating the generated Pyomo model...\n")
    deps_validator = ValidatorDeps(code=pyomo_code)
    validator_result = await suite.validator.run("", deps=deps_validator)
    validation_output = validator_result.output

    print("\n [Validation Results]:")
    print("Success:", validation_output.success)
    print("Error:", validation_output.error)
    print("\n--- Solver Output ---\n")
    print(validation_output.stdout)
    print("----------------------")
    print("Objective Name:", validation_output.objective_name)
    print("Objective Value:", validation_output.objective_value)

    print("\n Pipeline completed.\n")


if __name__ == "__main__":
    anyio.run(main)
