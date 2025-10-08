import asyncio
from agents import MyAgent


async def main():
    # --- Initialize Expert and Integrator ---
    expert = MyAgent("Expert")
    integrator = MyAgent("Integrator")

    # --- Optimization task prompt ---
    optimization_prompt = optimization_prompt = """
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

Goal: maximize total profit using the KKT system.
Write a complete Python function that calculates the optimal number of Tomato and Cucumber plants to grow.
"""

    # --- Expert generates Python code ---
    expert_code = await expert.solve_task(optimization_prompt)
    print("\n[Expert] Generated code:\n", expert_code)

    # --- Integrator reviews Expert's code ---
    integrator_prompt = f"""
    The Expert generated this Python code:\n{expert_code}\n
    """
    integrator_feedback = await integrator.solve_task(integrator_prompt)
    print("\n[Integrator] Feedback:\n", integrator_feedback)


if __name__ == "__main__":
    asyncio.run(main())
