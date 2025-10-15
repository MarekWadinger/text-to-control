import runpy

import anyio

from agents import ExpertDeps, IntegratorDeps, MyAgent


async def main():
    print("\n Starting Expert & Integrator Agents Pipeline...\n")

    # initialization of agents
    expert = MyAgent("Expert")
    integrator = MyAgent("Integrator")

    # desination of the optimization problem
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
Formulate and solve a Pyomo optimization model to maximize total profit.
Use SolverFactory('glpk') or SolverFactory('ipopt') as appropriate.
Show the final optimal values and total profit.
"""
    # --------------------------------------------------------

    deps_expert = ExpertDeps()
    expert_result = await expert.solve_task(
        optimization_prompt, deps=deps_expert
    )
    expert_output = expert_result.output

    print(" [Expert Explanation]:\n", expert_output.explanation)
    print("\n [Generated Pyomo Code Preview]:\n")
    print(expert_output.code[:600], "...\n")

    # --------------------------------------------------------

    with open("generated_code.py", "w", encoding="utf-8") as f:
        f.write(expert_output.code.strip())
    print(" Expert code saved to generated_code.py\n")

    # --------------------------------------------------------

    print(" Running generated Pyomo model...\n")
    try:
        result = runpy.run_path("generated_code.py")
        print("\n Model executed successfully!\n")

        if "model" in result:
            model = result["model"]
            try:
                print(
                    " Solver Status:",
                    model.solutions.load_from.results.solver.status,
                )
            except Exception:
                pass
        else:
            print(
                "ℹ Model variable not found, but script executed successfully."
            )
    except Exception as e:
        print(f" Error during model execution: {e}")

    # --------------------------------------------------------

    deps_integrator = IntegratorDeps(
        expert_code=expert_output.code,
    )
    integrator_prompt = f"""
You are the Integrator Agent. Review the following Pyomo code for:
1. Correctness (does it match the problem formulation?),
2. Efficiency (is the model well-structured?),
3. Best practices (naming, solver use, duals, etc.),
4. Suggestions for improvement.

Code to review:
{expert_output.code}
"""
    integrator_result = await integrator.solve_task(
        integrator_prompt, deps=deps_integrator
    )
    feedback = integrator_result.output

    print("\n [Integrator Feedback]")
    print("Correctness:", feedback.correctness)
    print("\nEfficiency:", feedback.efficiency)
    print("\nBest Practices:", feedback.best_practices)
    print("\nSuggestions:", feedback.improvement_suggestions)

    # --------------------------------------------------------

    print("\n Pipeline completed successfully.")
    print(
        " Agents collaborated to formulate, solve, and review the optimization model."
    )


if __name__ == "__main__":
    anyio.run(main)
